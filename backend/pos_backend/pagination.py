from rest_framework.pagination import PageNumberPagination

class OptionalPagination(PageNumberPagination):
    """
    A custom pagination class that defaults to no pagination unless the frontend 
    explicitly requests a 'page' or 'page_size' query parameter.
    This provides 100% backward compatibility for endpoints expecting raw arrays.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def paginate_queryset(self, queryset, request, view=None):
        if 'page' not in request.query_params and 'page_size' not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)
