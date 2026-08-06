import os

filepath = 'test_full_flows.py'
with open(filepath, 'r') as f:
    content = f.read()
content = content.replace("User.objects.create_superuser(username='testadmin', password='password123', email='admin@test.com')", "User.objects.create_superuser(password='password123', email='admin@test.com')")
with open(filepath, 'w') as f:
    f.write(content)
print('Fixed username issue')
