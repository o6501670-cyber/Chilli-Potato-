import re

html_file = 'frontend/src/app/dashboard/dashboard.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Summary Cards to make them look like the Dribbble image
# Card 1: Revenue (Huge)
content = re.sub(
    r'<div class="stat-row">\s*<span>Revenue This Period</span>\s*<span class="val">\{\{ summaryData.revenue \| currency:\'INR\':\'symbol\':\'1\.0-0\' \}\}</span>\s*</div>',
    r'<div class="card-title"><i class="fa-solid fa-wallet"></i> Revenue This Period</div>\n        <div class="hero-val">{{ summaryData.revenue | currency:\'INR\':\'symbol\':\'1.0-0\' }}</div>',
    content, count=1
)

# Replace Target Card with accent class
content = re.sub(
    r'<div class="stat-row">\s*<span>Monthly Target</span>\s*<span class="val">\{\{ summaryData\.target \| currency:\'INR\':\'symbol\':\'1\.0-0\'\s*\}\}</span>\s*</div>',
    r'</div>\n      <div class="dash-card dash-card-dark">\n        <div class="card-title"><i class="fa-solid fa-bullseye"></i> Monthly Target</div>\n        <div class="hero-val">{{ summaryData.target | currency:\'INR\':\'symbol\':\'1.0-0\' }}</div>\n      </div>\n      <div class="dash-card dash-card-accent">\n',
    content, count=1
)

# Fix Projected
content = re.sub(
    r'<div class="stat-row">\s*<span>Projected This Month</span>\s*<span class="val">\{\{ summaryData\.projected \| currency:\'INR\':\'symbol\':\'1\.0-0\'\s*\}\}</span>\s*</div>',
    r'<div class="card-title"><i class="fa-solid fa-arrow-trend-up"></i> Projected This Month</div>\n        <div class="hero-val">{{ summaryData.projected | currency:\'INR\':\'symbol\':\'1.0-0\' }}</div>',
    content, count=1
)

# And fix the stray closing div from the original first card wrapper
# Actually, the original HTML was:
# <div class="dash-card">
#   <div class="stat-row">Revenue</div>
#   <div class="stat-row">Target</div>
#   <div class="stat-row">Projected</div>
# </div>
# The above regex breaks it into three cards! Let's just do a clean replacement of that first card.
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated HTML for summary cards")
