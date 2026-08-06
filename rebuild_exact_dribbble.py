import re
import os

html_file = 'frontend/src/app/dashboard/dashboard.html'
css_file = 'frontend/src/app/dashboard/dashboard.css'
ts_file = 'frontend/src/app/dashboard/dashboard.ts'

# 1. THE EXACT DRIBBBLE CSS
new_css = """
:host {
  display: block;
  width: 100%;
  height: 100%;
  font-family: 'Inter', -apple-system, sans-serif;
  background: #fbfbfc; /* Exact faint off-white background from image */
  color: #111;
}

.dashboard-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 32px 40px;
  background: transparent;
  overflow-y: auto;
}

h1.main-title {
  font-size: 32px;
  font-weight: 700;
  color: #d1d5db; /* Very light grey like the image "New report" */
  margin-bottom: 24px;
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
  color: #9ca3af;
  font-weight: 600;
  font-size: 13px;
}

.location-select, .date-filters input {
  padding: 8px 16px;
  border-radius: 50px;
  border: 1px solid #f3f4f6;
  background: #ffffff;
  color: #111;
  font-size: 13px;
  font-weight: 600;
  outline: none;
  box-shadow: 0 2px 10px rgba(0,0,0,0.02);
}

/* Tabs */
.dashboard-tabs {
  display: inline-flex;
  gap: 4px;
  margin-bottom: 24px;
  align-self: flex-start;
}

.dash-tab {
  padding: 8px 24px;
  border: 1px solid #f3f4f6;
  background: #fff;
  color: #6b7280;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  border-radius: 50px;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.01);
}

.dash-tab:hover {
  color: #111;
}

.dash-tab.active {
  background: #111;
  color: #fff;
  border-color: #111;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

/* EXACT DRIBBBLE TOP ROW */
.dribbble-top-row {
  display: flex;
  gap: 24px;
  align-items: stretch;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.revenue-label { font-size: 18px; font-weight: 700; color: #111; margin-bottom: 8px; }
.hero-val { 
  font-size: 48px; 
  font-weight: 800; 
  letter-spacing: -1.5px; 
  color: #111; 
  display: flex; 
  align-items: center; 
  gap: 16px; 
  margin-bottom: 8px;
}
.vs-prev { font-size: 12px; color: #6b7280; font-weight: 500; margin-top: 4px; }

.badge { padding: 4px 12px; border-radius: 50px; font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; }
.badge-red { background: linear-gradient(135deg, #f43f5e, #e11d48); color: #fff; box-shadow: 0 4px 10px rgba(225, 29, 72, 0.2); }
.badge-grey { background: #f3f4f6; color: #6b7280; }

.drib-card {
  background: #fff;
  border-radius: 20px;
  padding: 16px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.03);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid #f9fafb;
  min-width: 140px;
  flex: 1;
}
.drib-card-dark { background: #111; color: #fff; border: none; box-shadow: 0 8px 30px rgba(0,0,0,0.15); }
.drib-card-dark .drib-title { color: #9ca3af; }
.drib-card-dark .drib-val { color: #fff; }

.drib-card-outline-grey { border: 1px solid #e5e7eb; box-shadow: none; }
.drib-card-outline-red { border: 1px solid #fda4af; background: #fff1f2; box-shadow: none; }
.drib-card-outline-red .drib-val { color: #e11d48; }
.drib-card-outline-red .drib-title { color: #e11d48; opacity: 0.8;}

.drib-title { font-size: 12px; color: #6b7280; font-weight: 500; margin-bottom: 12px; }
.drib-val { font-size: 24px; font-weight: 800; color: #111; margin-bottom: 8px;}
.drib-sub { font-size: 11px; color: #6b7280; margin-top: auto; font-weight: 600; display:flex; align-items:center; gap: 6px;}
.drib-sub .up { color: #10b981; }
.drib-sub .down { color: #ef4444; }

/* The Middle Row (Charts area) exactly like Dribbble */
.dribbble-mid-row {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}
.drib-col-left { flex: 0 0 250px; display: flex; flex-direction: column; gap: 24px; }
.drib-col-mid { flex: 0 0 300px; display: flex; flex-direction: column; gap: 24px; }
.drib-col-right { flex: 1; display: flex; flex-direction: column; gap: 24px; }

.chart-card {
  background: #fff;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.03);
  border: 1px solid #f9fafb;
}

.list-item-drib {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
  font-size: 13px;
  font-weight: 600;
  color: #111;
}
.list-item-drib:last-child { border-bottom: none; }
.list-item-drib .icon { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: #f3f4f6; color: #e11d48; margin-right: 12px; }
.list-item-drib .percent { color: #9ca3af; font-size: 11px; margin-left: 12px;}

.chart-title-drib { font-size: 14px; font-weight: 700; color: #111; margin-bottom: 24px; }

/* Global charts container for other tabs */
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
.chart-container { position: relative; width: 100%; height: 280px; }
"""
with open(css_file, 'w', encoding='utf-8') as f:
    f.write(new_css)

# 2. HTML OVERHAUL
with open(html_file, 'r', encoding='utf-8') as f:
    html_content = f.read()

summary_replacement = """
  <!-- TAB: SUMMARY -->
  <div class="tab-content" *ngIf="activeTab === 'summary' && !isLoading && summaryData">
    
    <h1 class="main-title">New report</h1>

    <div class="dribbble-top-row">
      <div style="flex: 1;">
        <div class="revenue-label">Revenue</div>
        <div class="hero-val">
          {{ summaryData.revenue | currency:'INR':'symbol':'1.0-0' }}
          <span class="badge badge-red"><i class="fa-solid fa-arrow-up"></i> Target: {{ summaryData.target | currency:'INR':'symbol':'1.0-0' }}</span>
        </div>
        <div class="vs-prev">vs prev. Projected {{ summaryData.projected | currency:'INR':'symbol':'1.0-0' }}</div>
      </div>

      <div style="display:flex; gap:16px; flex-wrap: wrap;">
        <!-- Card: Top sales -->
        <div class="drib-card">
          <div class="drib-title">New clients</div>
          <div class="drib-val">{{ summaryData.new_clients }}</div>
          <div class="drib-sub"><i class="fa-solid fa-user" style="color: #3b82f6;"></i> Just Joined</div>
        </div>

        <!-- Card: Best deal (Black) -->
        <div class="drib-card drib-card-dark">
          <div class="drib-title">Repeat clients</div>
          <div class="drib-val">{{ summaryData.repeat_clients }}</div>
          <div class="drib-sub" style="color: #9ca3af;"><i class="fa-solid fa-star" style="color: #fbbf24;"></i> Loyal</div>
        </div>

        <!-- Card: Deals (Outline) -->
        <div class="drib-card drib-card-outline-grey">
          <div class="drib-title" style="margin-bottom: 16px;">Total clients</div>
          <div class="badge badge-grey" style="align-self: flex-start;">{{ summaryData.total_clients }}</div>
          <div class="drib-sub"><i class="fa-solid fa-arrow-down down"></i> 5</div>
        </div>

        <!-- Card: Value (Red outline) -->
        <div class="drib-card drib-card-outline-red">
          <div class="drib-title" style="margin-bottom: 16px;">Inventory Value</div>
          <div class="badge badge-red" style="align-self: flex-start;">{{ summaryData.inventory.amount | currency:'INR':'symbol':'1.0-0' }}</div>
          <div class="drib-sub"><i class="fa-solid fa-arrow-up up"></i> {{ summaryData.inventory.count }} Items</div>
        </div>
      </div>
    </div>

    <!-- Exact mid row from image -->
    <div class="dribbble-mid-row">
      <!-- Left col: List of things -->
      <div class="drib-col-left">
        <div class="chart-card">
          <div class="chart-title-drib" style="display:flex; justify-content:space-between;">
            <i class="fa-solid fa-bars-staggered"></i> Filters <i class="fa-solid fa-chevron-down"></i>
          </div>
          <div class="list-item-drib" *ngFor="let p of summaryData?.top_products | slice:0:4">
            <div style="display:flex; align-items:center;">
              <div class="icon"><i class="fa-solid fa-box"></i></div>
              <span>{{ $any(p).name | slice:0:15 }}</span>
            </div>
            <div>
              <span>{{ $any(p).count }}</span>
              <span class="percent">items</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Mid col: Bar chart (Capsules) -->
      <div class="drib-col-mid">
        <div class="chart-card" style="height: 100%;">
          <div class="chart-title-drib" style="display:flex; justify-content:space-between;">
            <i class="fa-solid fa-chart-column"></i> <span style="font-size:12px; color:#6b7280; font-weight:500;">Filters <i class="fa-solid fa-chevron-down"></i></span>
          </div>
          <div style="position:relative; height: 180px; width:100%;">
            <canvas id="summaryBarChart"></canvas>
          </div>
          <div style="font-size: 13px; color: #6b7280; font-weight: 500; margin-top: 16px;">
            Revenue amount<br>by day category <i class="fa-solid fa-chevron-down"></i>
          </div>
        </div>
      </div>

      <!-- Right col: Huge Line chart area -->
      <div class="drib-col-right">
        <div class="chart-card" style="height: 100%; display: flex; flex-direction: column;">
          <div style="display:flex; justify-content: space-between; align-items: flex-end; margin-bottom: 24px;">
            <div>
              <div style="font-size: 14px; font-weight: 700; color: #111;">Revenue dynamic</div>
              <div style="font-size: 12px; color: #6b7280; font-weight: 500; margin-top: 4px;">W1 - W2 - W3 - W4</div>
            </div>
            <div>
              <span class="badge badge-red"><i class="fa-solid fa-arrow-up"></i> {{ summaryData.revenue | currency:'INR':'symbol':'1.0-0' }}</span>
            </div>
          </div>
          
          <div style="position:relative; flex: 1; width:100%; min-height: 200px;">
            <canvas id="summaryLineChart"></canvas>
          </div>
        </div>
      </div>

    </div>
"""

parts = html_content.split('<!-- TAB: SUMMARY -->')
before_summary = parts[0]
after_summary = parts[1].split('<!-- TAB: REVENUES -->')[1]
new_html = before_summary + summary_replacement + '\n  </div>\n\n  <!-- TAB: REVENUES -->' + after_summary

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(new_html)


# 3. TS CHART OVERHAUL
with open(ts_file, 'r', encoding='utf-8') as f:
    ts_content = f.read()

# Update Chart defaults to support the rounded capsule bars and smooth lines globally
new_defaults = """    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#9ca3af';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(17, 17, 17, 0.9)';
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 12;
    Chart.defaults.scale.grid.display = false;
    Chart.defaults.elements.bar.borderRadius = 100;
    Chart.defaults.elements.bar.borderSkipped = false;
    Chart.defaults.elements.line.tension = 0.4;
    Chart.defaults.elements.point.radius = 0;
    Chart.defaults.elements.point.hoverRadius = 6;
    Chart.defaults.animation = { duration: 1500, easing: 'easeOutQuart' };
"""
ts_content = re.sub(
    r'Chart\.defaults\.font\.family = [^;]+;[\s\S]*?(?=const today =)',
    new_defaults + '\n    ',
    ts_content
)

# Overwrite renderSummaryCharts to draw the exact charts from the image
ts_charts = """
  renderSummaryCharts() {
    if (!this.summaryData) return;
    
    // Bar Chart (Middle Col)
    const ctxBar = document.getElementById('summaryBarChart') as HTMLCanvasElement;
    if (ctxBar && this.summaryData.revenue_by_day) {
      const labels = this.summaryData.revenue_by_day.map((d: any) => d.day.slice(-5)); // Just DD-MM
      const data = this.summaryData.revenue_by_day.map((d: any) => d.revenue);
      this.charts['sumBar'] = new Chart(ctxBar, {
        type: 'bar',
        data: {
          labels,
          datasets: [{ data, backgroundColor: '#f3f4f6', hoverBackgroundColor: '#e11d48', barThickness: 24 }]
        },
        options: { 
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: { display: false }, y: { display: false } }
        }
      });
    }

    // Line Chart (Right Col)
    const ctxLine = document.getElementById('summaryLineChart') as HTMLCanvasElement;
    if (ctxLine && this.summaryData.revenue_by_day) {
      const labels = this.summaryData.revenue_by_day.map((d: any) => d.day);
      const data = this.summaryData.revenue_by_day.map((d: any) => d.revenue);
      
      const gradient = ctxLine.getContext('2d')?.createLinearGradient(0, 0, 0, 300);
      if (gradient) {
        gradient.addColorStop(0, 'rgba(225, 29, 72, 0.2)');
        gradient.addColorStop(1, 'rgba(225, 29, 72, 0)');
      }

      this.charts['sumLine'] = new Chart(ctxLine, {
        type: 'line',
        data: {
          labels,
          datasets: [{ 
            data, 
            borderColor: '#e11d48', 
            borderWidth: 2,
            backgroundColor: gradient || 'rgba(225, 29, 72, 0.1)', 
            fill: true,
          }]
        },
        options: { 
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: { display: false }, y: { display: false } }
        }
      });
    }
  }
"""

ts_content = re.sub(
    r'renderSummaryCharts\(\)\s*\{[\s\S]*?(?=// --- REVENUES CHARTS ---)',
    ts_charts + '\n  ',
    ts_content
)

with open(ts_file, 'w', encoding='utf-8') as f:
    f.write(ts_content)

print("Exact Dribbble Re-Injection complete")
