import re

html_file = 'frontend/src/app/dashboard/dashboard.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# The EXACT HTML snippet to replace the entire top section of the Summary Tab
dribbble_top_html = """
  <!-- TAB: SUMMARY -->
  <div class="tab-content" *ngIf="activeTab === 'summary' && !isLoading && summaryData">
    
    <h1 class="main-title">New report</h1>

    <div class="dribbble-top-row">
      <!-- Huge Revenue Block (Left) -->
      <div style="flex: 1;">
        <div class="revenue-label">Revenue</div>
        <div class="hero-val">
          {{ summaryData.revenue | currency:'INR':'symbol':'1.0-0' }}
          <span class="badge badge-red"><i class="fa-solid fa-bullseye"></i> Target: {{ summaryData.target | currency:'INR':'symbol':'1.0-0' }}</span>
        </div>
        <div class="vs-prev">vs prev. Projected {{ summaryData.projected | currency:'INR':'symbol':'1.0-0' }}</div>
      </div>

      <!-- Right small cards block -->
      <div style="display:flex; gap:12px; flex-wrap: wrap;">
        <!-- Card: Top sales (New Clients) -->
        <div class="drib-card">
          <div class="drib-title">New clients</div>
          <div class="drib-val">{{ summaryData.new_clients }}</div>
          <div class="drib-sub"><i class="fa-solid fa-user" style="color: #3b82f6;"></i> Just Joined</div>
        </div>

        <!-- Card: Best deal (Repeat Clients - Black) -->
        <div class="drib-card drib-card-dark">
          <div class="drib-title">Repeat clients</div>
          <div class="drib-val">{{ summaryData.repeat_clients }}</div>
          <div class="drib-sub" style="color: #9ca3af;"><i class="fa-solid fa-star" style="color: #fbbf24;"></i> Loyal</div>
        </div>

        <!-- Card: Deals (Total Clients - Outline) -->
        <div class="drib-card drib-card-outline-grey">
          <div class="drib-title" style="margin-bottom: 16px;">Total clients</div>
          <div class="badge badge-grey" style="align-self: flex-start;">{{ summaryData.total_clients }}</div>
          <div class="drib-sub"><i class="fa-solid fa-arrow-down down"></i> 5</div>
        </div>

        <!-- Card: Value (Inventory amount - Red outline) -->
        <div class="drib-card drib-card-outline-red">
          <div class="drib-title" style="margin-bottom: 16px;">Inventory Value</div>
          <div class="badge badge-red" style="align-self: flex-start;">{{ summaryData.inventory.amount | currency:'INR':'symbol':'1.0-0' }}</div>
          <div class="drib-sub"><i class="fa-solid fa-arrow-up up"></i> {{ summaryData.inventory.count }} Items</div>
        </div>
      </div>
    </div>

    <div class="dash-grid-top">
"""

# We need to find where the summary tab starts and where the first chart begins to replace everything in between.
# The summary tab starts at: <!-- TAB: SUMMARY -->
# And the first chart starts at: <div class="dash-grid-bottom"> (which contains the donut chart)
# Actually, the original HTML has <div class="dash-grid-top"> containing the old cards. We can replace that whole div.

start_pattern = r'<!-- TAB: SUMMARY -->\s*<div class="tab-content" \*ngIf="activeTab === \'summary\' && !isLoading && summaryData">\s*<div class="dash-grid-top">.*?</div>\s*</div>\s*<div class="dash-grid-bottom">'
# Wait, regex dotall is tricky here. Let's do it manually.

parts = content.split('<!-- TAB: SUMMARY -->')
before_summary = parts[0]
summary_and_after = parts[1]

# Split summary_and_after by the end of dash-grid-top
parts2 = summary_and_after.split('<div class="dash-grid-bottom">')
# The first part is the old summary cards. We replace it.
after_summary_cards = '<div class="dash-grid-bottom">' + parts2[1]

new_content = before_summary + dribbble_top_html + '\n    </div>\n\n    ' + after_summary_cards

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("HTML Replaced successfully")

