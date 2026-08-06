import os
import re

FRONTEND_DIR = r"frontend\src\app"
BACKEND_URLS_FILE = r"backend\backend_urls.txt"

# 1. Load Backend URLs
backend_urls = set()
with open(BACKEND_URLS_FILE, 'r', encoding='utf-16') as f:
    for line in f:
        line = line.strip()
        if line:
            backend_urls.add(line)

print(f"Found {len(backend_urls)} backend routes (including regex patterns).")

# 2. Extract Frontend API Calls
# Look for something like this.http.get<...>(`${this.apiUrl}/salon_admin/api/dashboard/`)
# Or this.apiService.get('/marketing/api/promotions/')

api_patterns = [
    re.compile(r"http(?:Client)?\.(?:get|post|put|delete|patch)[^('\"\`]+['\"\`]?([^\)'\"\`]+)['\"\`]?", re.IGNORECASE),
    re.compile(r"this\.apiUrl\s*\+\s*['\"`/]([^'\"`\?]+)", re.IGNORECASE),
    re.compile(r"`\$\{this\.apiUrl\}/([^`\?]+)`", re.IGNORECASE)
]

frontend_calls = set()

for root, _, files in os.walk(FRONTEND_DIR):
    for file in files:
        if file.endswith('.ts') or file.endswith('.js'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in api_patterns:
                    matches = pattern.findall(content)
                    for match in matches:
                        # Clean up matches
                        match = match.strip()
                        if 'api/' in match or match.startswith('/'):
                            # Try to extract just the path portion
                            clean_match = match.split('?')[0].split('${')[0]
                            if clean_match.startswith('this.apiUrl + '):
                                clean_match = clean_match.replace('this.apiUrl + ', '').strip('\'"/')
                            elif clean_match.startswith('/'):
                                clean_match = clean_match[1:]
                                
                            if clean_match and clean_match != 'api/':
                                frontend_calls.add(clean_match)
            except Exception as e:
                pass

print(f"\nFound {len(frontend_calls)} distinct API paths in frontend code:")
for call in sorted(frontend_calls):
    print(f" - {call}")

# 3. Simple cross-reference (manual heuristic for now)
print("\n--- Missing or Suspicious API Calls ---")
for call in sorted(frontend_calls):
    # A very naive check: does the frontend call string exist as a substring in any backend route regex?
    found = False
    for b_url in backend_urls:
        if call.strip('/') in b_url:
            found = True
            break
    if not found:
        print(f"[MISSING?] {call}")

