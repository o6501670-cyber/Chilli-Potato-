from datetime import date
from django.db import transaction
from .models import StaffTransfer, StaffToolTracker

def sync_staff_transfers_and_tools():
    """
    Checks for expired temporary staff transfers and expired tool tracking periods.
    Automatically resolves them by reverting the staff member's center and marking tools as returned.
    """
    today = date.today()
    
    with transaction.atomic():
        # 1. Resolve expired transfers
        expired_transfers = StaffTransfer.objects.filter(
            status='Active',
            end_date__lte=today,
            transfer_type='Temporary'
        )
        
        for transfer in expired_transfers:
            transfer.status = 'Completed'
            transfer.save()
            
            # Revert staff center back to the original center
            staff = transfer.staff
            staff.center = transfer.from_center
            staff.save()

        # 2. Resolve expired tools
        expired_tools = StaffToolTracker.objects.filter(
            status='Taken',
            expected_return_date__lte=today
        )
        
        for tool in expired_tools:
            tool.status = 'Returned'
            tool.actual_return_date = today
            tool.save()
