import os
import re

html_file = 'frontend/src/app/dashboard/dashboard.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Clean up Services & Products inline styles
content = content.replace('style="color: #6b7280; font-weight: normal; font-size: 14px;"', '')
content = content.replace('style="height: 300px; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-bottom: 10px;"', '')
content = content.replace('style="width: 100%; border-collapse: collapse; font-size: 13px;"', '')
content = content.replace('style="text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: bold; color: #1f2937;"', '')
content = content.replace('style="border-bottom: 1px solid #f3f4f6;"', '')
content = content.replace('style="padding: 8px 0;"', '')
content = content.replace('style="padding: 8px 0; text-align: right;"', 'class="num"')
content = content.replace('style="padding: 6px 0;"', '')
content = content.replace('style="padding: 6px 0; text-align: right;"', 'class="num"')

# We will also add `<div class="chart-wrapper">` inside the `.chart-container` to avoid fixed height overriding
# Actually, the height is just 300px which is fine in `.chart-container` css now.

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print('Cleaned inline styles in dashboard.html')
