from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, IntegerField, Q, Value, When
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from apps.stores.models import Inventory

from .cache import build_search_cache_key
from .serializers import ProductSearchResultSerializer

TRUE_VALUES = {"1", "true", "True", "yes"}


class ProductSearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


SEARCH_PARAMETERS = [
    OpenApiParameter("q", OpenApiTypes.STR, description="Keyword — matches title, description, category name."),
    OpenApiParameter("category", OpenApiTypes.STR, description="Category id or exact name."),
    OpenApiParameter("price_min", OpenApiTypes.NUMBER, description="Minimum price (inclusive)."),
    OpenApiParameter("price_max", OpenApiTypes.NUMBER, description="Maximum price (inclusive)."),
    OpenApiParameter("store_id", OpenApiTypes.INT, description="Restrict to products stocked at this store; also attaches store_quantity to each result."),
    OpenApiParameter("in_stock", OpenApiTypes.BOOL, description="true = quantity > 0 (at store_id if given, else any store)."),
    OpenApiParameter("sort", OpenApiTypes.STR, enum=["price", "newest", "relevance"], description="Default: relevance."),
    OpenApiParameter("page", OpenApiTypes.INT),
    OpenApiParameter("page_size", OpenApiTypes.INT, description="Default 20, max 100."),
]


class ProductSearchView(APIView):
    """GET /api/search/products/

    Keyword search over title/description/category, with category,
    price range, store_id, and in_stock filters; sort by price, newest,
    or relevance; paginated; cached in Redis (see apps.search.cache).
    """

    pagination_class = ProductSearchPagination

    @extend_schema(
        parameters=SEARCH_PARAMETERS,
        responses={200: ProductSearchResultSerializer(many=True)},
    )
    def get(self, request):
        params = request.query_params
        q = params.get("q", "").strip()
        category = params.get("category")
        price_min = params.get("price_min")
        price_max = params.get("price_max")
        store_id = params.get("store_id")
        in_stock = params.get("in_stock")
        sort = params.get("sort", "relevance")
        page = params.get("page", "1")
        page_size = params.get("page_size", str(self.pagination_class.page_size))

        cache_key = build_search_cache_key(
            {
                "q": q,
                "category": category or "",
                "price_min": price_min or "",
                "price_max": price_max or "",
                "store_id": store_id or "",
                "in_stock": in_stock or "",
                "sort": sort,
                "page": page,
                "page_size": page_size,
            }
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        queryset = self._build_queryset(
            q, category, price_min, price_max, store_id, in_stock, sort
        )

        paginator = self.pagination_class()
        page_obj = paginator.paginate_queryset(queryset, request, view=self)
        self._attach_store_quantity(page_obj, store_id)

        serializer = ProductSearchResultSerializer(page_obj, many=True)
        response = paginator.get_paginated_response(serializer.data)
        cache.set(cache_key, response.data, timeout=settings.SEARCH_CACHE_TTL_SECONDS)
        return response

    def _build_queryset(self, q, category, price_min, price_max, store_id, in_stock, sort):
        queryset = Product.objects.select_related("category")

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(category__name__icontains=q)
            )
            queryset = queryset.annotate(
                relevance=Case(
                    When(title__iexact=q, then=Value(0)),
                    When(title__istartswith=q, then=Value(1)),
                    When(title__icontains=q, then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                )
            )
        else:
            queryset = queryset.annotate(
                relevance=Value(3, output_field=IntegerField())
            )

        if category:
            if category.isdigit():
                queryset = queryset.filter(category_id=int(category))
            else:
                queryset = queryset.filter(category__name__iexact=category)

        if price_min:
            queryset = queryset.filter(price__gte=price_min)
        if price_max:
            queryset = queryset.filter(price__lte=price_max)

        wants_in_stock = in_stock in TRUE_VALUES
        if store_id:
            queryset = queryset.filter(inventory_rows__store_id=store_id)
            if wants_in_stock:
                queryset = queryset.filter(
                    inventory_rows__store_id=store_id, inventory_rows__quantity__gt=0
                )
        elif wants_in_stock:
            queryset = queryset.filter(inventory_rows__quantity__gt=0)

        queryset = queryset.distinct()

        if sort == "price":
            queryset = queryset.order_by("price", "id")
        elif sort == "newest":
            queryset = queryset.order_by("-created_at", "id")
        else:
            queryset = queryset.order_by("relevance", "title", "id")

        return queryset

    def _attach_store_quantity(self, page_obj, store_id):
        if not store_id:
            for product in page_obj:
                product.store_quantity = None
            return
        product_ids = [product.id for product in page_obj]
        qty_map = dict(
            Inventory.objects.filter(
                store_id=store_id, product_id__in=product_ids
            ).values_list("product_id", "quantity")
        )
        for product in page_obj:
            product.store_quantity = qty_map.get(product.id, 0)


class AutocompleteView(APIView):
    """GET /api/search/suggest/?q=xxx

    Requires >=3 chars, returns up to 10 titles, prefix matches first.
    """

    MIN_QUERY_LENGTH = 3
    MAX_RESULTS = 10

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "q",
                OpenApiTypes.STR,
                required=True,
                description="Minimum 3 characters. Fewer returns an empty result list.",
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "results": {"type": "array", "items": {"type": "string"}}
                },
            }
        },
    )
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < self.MIN_QUERY_LENGTH:
            return Response({"results": []})

        titles = (
            Product.objects.filter(title__icontains=q)
            .annotate(
                rank=Case(
                    When(title__istartswith=q, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by("rank", "title")
            .values_list("title", flat=True)[: self.MAX_RESULTS]
        )
        return Response({"results": list(titles)})
