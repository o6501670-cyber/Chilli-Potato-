from rest_framework import filters, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from pos_backend.permissions import IsOwner

from .models import SystemLog
from .serializers import SystemLogSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

class SystemLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SystemLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['user_name', 'user_email', 'path', 'human_description', 'ip_address', 'center_name']

    def get_queryset(self):
        user = self.request.user
        is_owner = IsOwner.check_is_owner(user)
        if not is_owner:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to view system logs.")

        qs = SystemLog.objects.all()

        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)

        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(module=module)

        center_id = self.request.query_params.get('center_id')
        if center_id:
            qs = qs.filter(center_id=center_id)

        start_date = self.request.query_params.get('start_date')
        if start_date:
            qs = qs.filter(timestamp__gte=f"{start_date} 00:00:00")

        end_date = self.request.query_params.get('end_date')
        if end_date:
            qs = qs.filter(timestamp__lte=f"{end_date} 23:59:59")

        user_email = self.request.query_params.get('user_email')
        if user_email:
            qs = qs.filter(user_email__icontains=user_email)

        return qs
