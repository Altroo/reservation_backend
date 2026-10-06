from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    def paginate_queryset(self, queryset, request, view=None):
        from reservation_backend.ordering import apply_list_ordering

        queryset = apply_list_ordering(queryset, request.query_params)
        return super().paginate_queryset(queryset, request, view)

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
