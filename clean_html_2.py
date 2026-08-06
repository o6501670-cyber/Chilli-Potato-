import os
import re

html_file = 'frontend/src/app/dashboard/dashboard.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Aggressive clean up of bad inline styles
content = content.replace('style="color:var(--text-color);"', '')
content = content.replace('style="border-bottom: 2px solid var(--primary-color); padding-bottom:5px;"', '')
content = content.replace('style="border-bottom: 2px solid var(--primary-color);"', '')
content = content.replace('style="margin-bottom:15px;"', '')
content = content.replace('style="margin-bottom:10px; font-weight:bold;"', 'class="card-title"')
content = content.replace('style="margin-top:15px;"', '')
content = content.replace('style="margin-bottom:8px;"', '')
content = content.replace('style="display:flex; justify-content:center; align-items:center; min-height: 250px;"', '')
content = content.replace('style="position:relative; width:200px; height:200px;"', '')

# Grid Overrides
content = content.replace('style="grid-template-columns: 1fr 2fr;"', 'class="dash-grid-2"')
content = content.replace('style="grid-template-columns: 1.5fr 2fr;"', 'class="dash-grid-2"')
content = content.replace('style="grid-template-columns: 1fr 1fr 1fr; gap:10px;"', '')
content = content.replace('style="grid-template-columns: 1fr 1fr;"', 'class="dash-grid-2"')
content = content.replace('style="grid-template-columns: 1fr 1fr 1.5fr;"', '')

content = re.sub(r'style="height:\s*\d+px;"', '', content)
content = content.replace('style="flex-direction:column; align-items:center; text-align:center;"', '')

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print('Cleaned aggressive inline styles')
