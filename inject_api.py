import os

filepath = r'frontend/src/app/services/api.ts'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import_str = """
  bulkUploadStaff(data: FormData): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}staff/bulk_upload/`, data, { headers: this.getHeaders(true) });
  }
"""

target = "createStaffMember(data: any): Observable<any> {"
if target in content and 'bulkUploadStaff' not in content:
    content = content.replace(target, import_str + "\n  " + target)
    
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
