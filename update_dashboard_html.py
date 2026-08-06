import os
import re

html_file = 'frontend/src/app/dashboard/dashboard.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Add the new tab button
if "activeTab === 'services_products'" not in content:
    content = content.replace(
        '<button class="dash-tab" [class.active]="activeTab === \'staff\'" (click)="setTab(\'staff\')">Staff</button>',
        '<button class="dash-tab" [class.active]="activeTab === \'services_products\'" (click)="setTab(\'services_products\')">Services & Products</button>\n    <button class="dash-tab" [class.active]="activeTab === \'staff\'" (click)="setTab(\'staff\')">Staff</button>'
    )

# Add to date-filters ngIf
if "activeTab === 'services_products'" not in content:
    # Actually wait, the date-filters condition is:
    # *ngIf="activeTab === 'summary' || activeTab === 'staff' || activeTab === 'clients'"
    content = content.replace(
        "activeTab === 'summary' || activeTab === 'staff' || activeTab === 'clients'",
        "activeTab === 'summary' || activeTab === 'staff' || activeTab === 'clients' || activeTab === 'services_products'"
    )

# The new Services & Products view
services_products_html = '''
  <!-- TAB: SERVICES & PRODUCTS -->
  <div class="tab-content" *ngIf="activeTab === 'services_products' && !isLoading && servicesProductsData">
    <div class="dash-grid-2">
      <!-- Services Column -->
      <div class="dash-card">
        <div class="card-title" style="color: #6b7280; font-weight: normal; font-size: 14px;">Service Category Sales</div>
        <div class="chart-container" style="height: 300px; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-bottom: 10px;">
          <canvas id="serviceCategoryChart"></canvas>
        </div>
        <table class="stat-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: bold; color: #1f2937;">
              <th style="padding: 8px 0;">Service Type</th>
              <th style="padding: 8px 0; text-align: right;">Count</th>
              <th style="padding: 8px 0; text-align: right;">Revenue</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let s of servicesProductsData.services" style="border-bottom: 1px solid #f3f4f6;">
              <td style="padding: 6px 0;">{{ s.name }}</td>
              <td style="padding: 6px 0; text-align: right;">{{ s.count }}</td>
              <td style="padding: 6px 0; text-align: right;">{{ s.revenue | number:'1.0-0' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Products Column -->
      <div class="dash-card">
        <div class="card-title" style="color: #6b7280; font-weight: normal; font-size: 14px;">Product Category Sales</div>
        <div class="chart-container" style="height: 300px; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-bottom: 10px;">
          <canvas id="productCategoryChart"></canvas>
        </div>
        <table class="stat-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: bold; color: #1f2937;">
              <th style="padding: 8px 0;">Product Type</th>
              <th style="padding: 8px 0; text-align: right;">Count</th>
              <th style="padding: 8px 0; text-align: right;">Revenue</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let p of servicesProductsData.products" style="border-bottom: 1px solid #f3f4f6;">
              <td style="padding: 6px 0;">{{ p.name }}</td>
              <td style="padding: 6px 0; text-align: right;">{{ p.count }}</td>
              <td style="padding: 6px 0; text-align: right;">{{ p.revenue | number:'1.0-0' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
'''

if '<!-- TAB: SERVICES & PRODUCTS -->' not in content:
    content = content.replace('<!-- TAB: STAFF -->', services_products_html + '\n  <!-- TAB: STAFF -->')

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated dashboard.html")
