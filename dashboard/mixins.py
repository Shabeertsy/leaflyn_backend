from django.core.paginator import Paginator

class PaginationSearchMixin:
    paginate_by = 10  # default items per page
    search_fields = []  # to be overridden in view
    fields = []  # filter fields to be overridden in view

    def get_search_query(self, request):
        return request.GET.get('q', '').strip()

    def get_filter_fields(self, request):
        """
        Returns a dict of filter fields defined in the `fields` class variable.
        """
        return {
            field: request.GET.get(field, '').strip()
            for field in getattr(self, 'fields', [])
        }

    def filter_queryset(self, queryset, search_query, filter_fields):
        """
        Filters queryset by search_query (search_fields) and filter_fields (exact/contains match).
        Works with iterables of objects, not just QuerySets.
        """
        # Search filter
        if search_query and self.search_fields:
            search_query_lower = search_query.lower()
            queryset = [
                obj for obj in queryset
                if any(
                    search_query_lower in str(getattr(obj, attr, '')).lower()
                    for attr in self.search_fields
                )
            ]

        # Field filters
        for field, value in filter_fields.items():
            if value:
                queryset = [
                    obj for obj in queryset
                    if hasattr(obj, field) and value.lower() in str(getattr(obj, field, '')).lower()
                ]
        return queryset

    def paginate_queryset(self, request, queryset):
        page_number = request.GET.get('page', 1)
        paginator = Paginator(queryset, self.paginate_by)
        try:
            page_obj = paginator.page(page_number)
        except Exception:
            page_obj = paginator.page(1)
        return page_obj

    def get_filtered_paginated_queryset(self, request, queryset):
        search_query = self.get_search_query(request)
        filter_fields = self.get_filter_fields(request)
        filtered_queryset = self.filter_queryset(queryset, search_query, filter_fields)
        paginated_queryset = self.paginate_queryset(request, filtered_queryset)
        return paginated_queryset, search_query, filter_fields
