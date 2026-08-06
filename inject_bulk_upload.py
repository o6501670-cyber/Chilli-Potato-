import os

filepath = r'backend/staff/views.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import_str = """from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
import openpyxl
from datetime import datetime
from decimal import Decimal
from salon_admin.models import Center
"""

if 'import openpyxl' not in content:
    content = content.replace("from rest_framework import viewsets, permissions, status", import_str + "from rest_framework import viewsets, permissions, status")

bulk_upload_method = """
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_upload(self, request):
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided'}, status=400)
            
        excel_file = request.FILES['file']
        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            sheet = wb.active
        except Exception as e:
            return Response({'detail': f'Error reading Excel file: {str(e)}'}, status=400)

        rows = list(sheet.iter_rows(values_only=True))
        if len(rows) < 2:
            return Response({'detail': 'File is empty or missing headers'}, status=400)
            
        header = [str(h).strip().lower() if h else '' for h in rows[0]]
        
        success_count = 0
        errors = []
        
        for i, row in enumerate(rows[1:], start=2):
            # Create a dict from header to row values
            row_data = dict(zip(header, row))
            
            # Extract basic info
            raw_name = str(row_data.get('name') or '').strip()
            if not raw_name:
                continue # Skip empty rows
                
            parts = raw_name.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''
            
            # Map Center
            loc_name = str(row_data.get('location name') or row_data.get('location') or '').strip()
            center = None
            if loc_name:
                center = Center.objects.filter(center_name__icontains=loc_name).first()
            
            if not center:
                errors.append(f"Row {i}: Could not find Center matching '{loc_name}'")
                continue
                
            # Parse Designation and Gender
            designation = str(row_data.get('designation') or '').strip()
            gender = str(row_data.get('gender') or '').strip().capitalize()
            if gender not in ['Male', 'Female', 'Other']:
                gender = 'Female'
                
            # Parse Salary
            raw_salary = row_data.get('monthly gross') or 0
            try:
                salary = Decimal(str(raw_salary))
            except Exception:
                salary = Decimal('0.0')
                
            # Parse Date
            raw_date = row_data.get('join date')
            joining_date = None
            if raw_date:
                if isinstance(raw_date, datetime):
                    joining_date = raw_date.date()
                else:
                    try:
                        # try string format e.g. "13 Apr 2026"
                        joining_date = datetime.strptime(str(raw_date).strip(), '%d %b %Y').date()
                    except ValueError:
                        pass
                        
            # Create Staff Member
            try:
                StaffMember.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    center=center,
                    designation=designation,
                    gender=gender,
                    salary=salary,
                    joining_date=joining_date,
                    is_active=True
                )
                success_count += 1
            except Exception as e:
                errors.append(f"Row {i}: Error saving staff '{first_name}' - {str(e)}")
                
        return Response({
            'detail': f'Successfully uploaded {success_count} staff members.',
            'errors': errors
        })
"""

# inject right before perform_create
target = "    def perform_create(self, serializer):"
if 'def bulk_upload' not in content:
    content = content.replace(target, bulk_upload_method + "\n" + target)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
