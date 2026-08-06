import re

# 1. Update CSS
css_file = 'frontend/src/app/dashboard/dashboard.css'
new_css = """
:host {
  display: block;
  width: 100%;
  height: 100%;
  font-family: 'Inter', -apple-system, sans-serif;
  background: #f8fafc;
  color: #334155;
}

.dashboard-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 32px;
  background: transparent;
  overflow-y: auto;
}

/* Header & Controls */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-controls {
  display: flex;
  gap: 16px;
  align-items: center;
}

.header-controls label, .date-filters label {
  color: #64748b;
  font-weight: 600;
  font-size: 14px;
}

.location-select, .date-filters input {
  padding: 10px 16px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  font-size: 14px;
  font-weight: 500;
  outline: none;
  transition: all 0.2s;
}

.location-select:focus, .date-filters input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Tabs */
.dashboard-tabs {
  display: inline-flex;
  gap: 8px;
  margin-bottom: 32px;
  align-self: flex-start;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 8px;
  width: 100%;
}

.dash-tab {
  padding: 8px 16px;
  background: transparent;
  border: none;
  color: #64748b;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.dash-tab:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.dash-tab.active {
  background: #eff6ff;
  color: #2563eb;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.metric-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  transition: transform 0.2s, box-shadow 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(0,0,0,0.08);
}

.gradient-primary {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #fff;
  border: none;
}
.gradient-primary .m-title, .gradient-primary .m-sub { color: #94a3b8; }

.m-title { 
  font-size: 13px; 
  font-weight: 600; 
  color: #64748b; 
  margin-bottom: 16px; 
  text-transform: uppercase; 
  letter-spacing: 0.5px;
}

.m-val { 
  font-size: 36px; 
  font-weight: 700; 
  margin-bottom: 8px; 
  letter-spacing: -0.5px;
}
.text-primary { color: #2563eb; }

.m-sub { 
  font-size: 14px; 
  color: #64748b; 
  font-weight: 500;
}

/* Charts Area */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}
.dash-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 24px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 16px;
}
.chart-container {
  position: relative;
  width: 100%;
  height: 280px; /* Reduced height to keep charts smaller */
}

/* Tables */
.stat-table {
  width: 100%;
  font-size: 14px;
  border-collapse: collapse;
}
.stat-table th, .stat-table td {
  padding: 16px 12px;
  text-align: left;
  border-bottom: 1px solid #f1f5f9;
}
.stat-table th { 
  color: #64748b; 
  font-weight: 600; 
  font-size: 12px; 
  text-transform: uppercase;
}
.stat-table tbody tr:hover { background: #f8fafc; }
.stat-table .num { text-align: right; font-weight: 600; }
"""
with open(css_file, 'w', encoding='utf-8') as f:
    f.write(new_css)

# 2. Update HTML Summary Tab
html_file = 'frontend/src/app/dashboard/dashboard.html'
with open(html_file, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Replace the entire Summary Tab
summary_replacement = """
  <!-- TAB: SUMMARY -->
  <div class="tab-content" *ngIf="activeTab === 'summary' && !isLoading && summaryData">
    
    <div class="metrics-grid">
      <div class="metric-card gradient-primary">
        <div class="m-title">Total Revenue</div>
        <div class="m-val">{{ summaryData.revenue | currency:'INR':'symbol':'1.0-0' }}</div>
        <div class="m-sub"><i class="fa-solid fa-bullseye"></i> Target: {{ summaryData.target | currency:'INR':'symbol':'1.0-0' }}</div>
      </div>
      
      <div class="metric-card">
        <div class="m-title">Projected Revenue</div>
        <div class="m-val text-primary">{{ summaryData.projected | currency:'INR':'symbol':'1.0-0' }}</div>
        <div class="m-sub"><i class="fa-solid fa-chart-line"></i> End of month estimate</div>
      </div>
      
      <div class="metric-card">
        <div class="m-title">Client Footfall</div>
        <div class="m-val">{{ summaryData.new_clients }} <span style="color:#cbd5e1; font-weight:400;">/</span> {{ summaryData.repeat_clients }}</div>
        <div class="m-sub">New vs Repeat (Total: {{ summaryData.total_clients }})</div>
      </div>

      <div class="metric-card">
        <div class="m-title">Inventory Value</div>
        <div class="m-val">{{ summaryData.inventory.amount | currency:'INR':'symbol':'1.0-0' }}</div>
        <div class="m-sub"><i class="fa-solid fa-box"></i> {{ summaryData.inventory.count }} total items</div>
      </div>
    </div>

    <div class="charts-grid">
      <div class="dash-card">
        <div class="card-title">Revenue & Projection</div>
        <div class="chart-container">
          <canvas id="summaryDonutChart"></canvas>
        </div>
      </div>

      <div class="dash-card">
        <div class="card-title">Top Moving Inventory</div>
        <table class="stat-table">
          <thead>
            <tr>
              <th>Item Name</th>
              <th class="num">Quantity Sold</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let p of summaryData?.top_products | slice:0:5">
              <td>{{ $any(p).name }}</td>
              <td class="num">{{ $any(p).count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
"""

# Inject using the same logic (split by <!-- TAB: SUMMARY -->)
parts = html_content.split('<!-- TAB: SUMMARY -->')
before_summary = parts[0]
after_summary = parts[1].split('<!-- TAB: REVENUES -->')[1]

new_html = before_summary + summary_replacement + '\n  </div>\n\n  <!-- TAB: REVENUES -->' + after_summary

# Replace dash-grid-2 / dash-grid-top classes globally to just charts-grid if they are still there
new_html = new_html.replace('class="dash-grid-top"', 'class="charts-grid"')
new_html = new_html.replace('class="dash-grid-2"', 'class="charts-grid"')
new_html = new_html.replace('class="dash-grid-bottom"', 'class="charts-grid"')

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(new_html)

# 3. Update dashboard.ts Chart Defaults
ts_file = 'frontend/src/app/dashboard/dashboard.ts'
with open(ts_file, 'r', encoding='utf-8') as f:
    ts_content = f.read()

new_defaults = """    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#64748b';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.95)';
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 6;
    Chart.defaults.scale.grid.display = true;
    Chart.defaults.scale.grid.color = 'rgba(0,0,0,0.04)';
    Chart.defaults.scale.ticks.color = '#94a3b8';
    Chart.defaults.elements.bar.borderRadius = 4;
    Chart.defaults.elements.bar.borderSkipped = 'bottom';
    Chart.defaults.elements.line.tension = 0.2;
    Chart.defaults.elements.point.radius = 4;
    Chart.defaults.elements.point.hoverRadius = 6;
    Chart.defaults.animation = { duration: 1200, easing: 'easeOutQuart' };
"""

ts_content = re.sub(
    r'Chart\.defaults\.font\.family = [^;]+;[\s\S]*?(?=const today =)',
    new_defaults + '\n    ',
    ts_content
)

with open(ts_file, 'w', encoding='utf-8') as f:
    f.write(ts_content)

print("Professional aesthetic overhaul complete")
