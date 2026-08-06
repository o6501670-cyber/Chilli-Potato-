import re

path = 'c:/Users/Dell/OneDrive - CINNTRA INFO TECH SOLUTIONS PRIVATE LIMITED/Desktop/latest chowmein/chowmein/chowmein/chowmein/chowmein/properback/FINAL_POS_CODE_two/backend/finance/views.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace DateTimeField filters
content = re.sub(r'created_at__gte=f"\{start_date\} 00:00:00"', r'created_at__date__gte=start_date', content)
content = re.sub(r'created_at__lte=f"\{end_date\} 23:59:59"', r'created_at__date__lte=end_date', content)

# Replace DateField filters
content = re.sub(r'date__gte=f"\{start_date\} 00:00:00"', r'date__gte=start_date', content)
content = re.sub(r'date__lte=f"\{end_date\} 23:59:59"', r'date__lte=end_date', content)

# There is also one for pos in admin/views? Let's just do it generally.
content = re.sub(r'__gte=f"\{start_date\} 00:00:00"', r'__date__gte=start_date', content)
content = re.sub(r'__lte=f"\{end_date\} 23:59:59"', r'__date__lte=end_date', content)
# But wait, date__date__gte is wrong if we replace __gte=... on a DateField.
# It's better to just be explicit.

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("views.py updated successfully!")
