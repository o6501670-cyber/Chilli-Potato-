import os
import re

ts_file = 'frontend/src/app/dashboard/dashboard.ts'
with open(ts_file, 'r', encoding='utf-8') as f:
    ts_content = f.read()

# Add servicesProductsData to properties
if 'servicesProductsData: any = null;' not in ts_content:
    ts_content = ts_content.replace('staffData: any = null;', 'staffData: any = null;\n  servicesProductsData: any = null;')

# Add to setTab
if "if (tab === 'services_products') this.loadServicesProducts();" not in ts_content:
    ts_content = ts_content.replace("if (tab === 'staff') this.loadStaff();", "if (tab === 'staff') this.loadStaff();\n    if (tab === 'services_products') this.loadServicesProducts();")

# Add loadServicesProducts method
load_sp_method = '''
  loadServicesProducts() {
    this.isLoading = true;
    this.apiService.getDashboardServicesProducts(this.getCenterId(), this.startDate, this.endDate).subscribe({
      next: (res) => {
        this.servicesProductsData = res;
        this.isLoading = false;
        setTimeout(() => this.renderServicesProductsCharts(), 150);
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error(err);
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }
'''
if 'loadServicesProducts()' not in ts_content:
    ts_content = ts_content.replace('loadStaff() {', load_sp_method + '\n  loadStaff() {')

# Add renderServicesProductsCharts method
render_sp_charts = '''
  renderServicesProductsCharts() {
    if (!this.servicesProductsData) return;

    const renderCombo = (id: string, label: string, dataKey: string, dataList: any[], color: string) => {
      const ctx = document.getElementById(id) as HTMLCanvasElement;
      if (!ctx) return;
      this.charts[id] = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: dataList.map((d: any) => d.name),
          datasets: [
            {
              type: 'bar',
              label: 'Revenue',
              data: dataList.map((d: any) => d.revenue),
              backgroundColor: color,
              yAxisID: 'y'
            },
            {
              type: 'line',
              label: 'Count',
              data: dataList.map((d: any) => d.count),
              borderColor: '#1e293b',
              backgroundColor: '#1e293b',
              borderWidth: 2,
              tension: 0.3,
              pointRadius: 4,
              yAxisID: 'y1'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          scales: {
            y: { type: 'linear', position: 'left', title: { display: true, text: 'Revenue' } },
            y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Counts' } }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    };

    renderCombo('serviceCategoryChart', 'Service Category Sales', 'services', this.servicesProductsData.services || [], '#38bdf8');
    renderCombo('productCategoryChart', 'Product Category Sales', 'products', this.servicesProductsData.products || [], '#3b82f6');
  }
'''
if 'renderServicesProductsCharts()' not in ts_content:
    ts_content = ts_content.replace('renderStaffCharts() {', render_sp_charts + '\n  renderStaffCharts() {')

with open(ts_file, 'w', encoding='utf-8') as f:
    f.write(ts_content)

print("Updated dashboard.ts")
