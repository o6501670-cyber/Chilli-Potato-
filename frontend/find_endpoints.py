import re
with open(r'src\app\finance\finance.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

endpoints = re.findall(r'this\.\w+\.(?:get|post|put)\([\'\"\`]([^\'\"\`]+)[\'\"\`]', ts_content)
print('Endpoints used in finance.ts:')
for ep in set(endpoints):
    print(ep)
