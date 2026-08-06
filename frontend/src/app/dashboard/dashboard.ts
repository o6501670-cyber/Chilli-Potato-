import { Component, OnInit, OnDestroy, inject, ChangeDetectorRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import Chart from 'chart.js/auto';
import { LocationSelectorComponent } from '../components/location-selector/location-selector';

Chart.defaults.font.family = 'Inter, sans-serif';
Chart.defaults.color = '#9ca3af';
Chart.defaults.scale.grid.color = 'rgba(0,0,0,0.035)';
// @ts-ignore
Chart.defaults.scale.grid.borderDash = [5, 5];
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(17, 24, 39, 0.95)';
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.displayColors = false;
Chart.defaults.plugins.tooltip.titleFont = { size: 13, family: 'Inter, sans-serif', weight: 'bold' };
Chart.defaults.plugins.tooltip.bodyFont = { size: 12, family: 'Inter, sans-serif', weight: 'normal' };
Chart.defaults.elements.bar.borderRadius = 4;
Chart.defaults.elements.bar.borderSkipped = false;
Chart.defaults.elements.line.tension = 0.4;
Chart.defaults.elements.line.borderWidth = 3;

const dataLabelsPlugin = {
  id: 'dataLabelsPlugin',
  afterDatasetsDraw(chart: any) {
    const { ctx } = chart;
    const drawnBoxes: { x: number, y: number, w: number, h: number }[] = [];
    
    // Process datasets in reverse so later datasets (often lower values) yield to earlier ones, or whatever order
    chart.data.datasets.forEach((dataset: any, i: number) => {
      const meta = chart.getDatasetMeta(i);
      if (meta.type !== 'bar' && meta.type !== 'line') return;

      meta.data.forEach((element: any, index: number) => {
        const rawVal = dataset.data[index];
        if (rawVal == null || rawVal === 0) return; // Skip 0 or null

        const valStr = String(rawVal);
        ctx.font = 'bold 10px Inter, sans-serif';
        const textWidth = ctx.measureText(valStr).width;
        
        const padX = 6;
        const padY = 4;
        const w = textWidth + padX * 2;
        const h = 10 + padY * 2; // 10px font height approx
        
        let lx = element.x - w / 2;
        let ly = element.y - h - 6; // start above point
        
        // Simple collision detection
        let maxTries = 5;
        let shift = 16; // shift up by 16px if collision
        while (maxTries > 0) {
          let collides = drawnBoxes.some(b => {
            return lx < b.x + b.w + 2 && lx + w + 2 > b.x &&
                   ly < b.y + b.h + 2 && ly + h + 2 > b.y;
          });
          if (collides) {
            ly -= shift; // push up
            maxTries--;
          } else {
            break;
          }
        }
        
        // If it goes above canvas, push it below the point instead
        if (ly < 0) {
          ly = element.y + 6;
          // check collision below
          let colBelow = drawnBoxes.some(b => lx < b.x + b.w && lx + w > b.x && ly < b.y + b.h && ly + h > b.y);
          if (colBelow) ly += shift;
        }

        drawnBoxes.push({ x: lx, y: ly, w, h });

        ctx.save();
        // Draw pill background
        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = dataset.borderColor || dataset.backgroundColor || '#64748b';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(lx, ly, w, h, 4);
        ctx.fill();
        ctx.stroke();

        // Draw text
        ctx.fillStyle = '#334155';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(valStr, lx + w / 2, ly + h / 2 + 1); // +1 for visual vertical center
        ctx.restore();
      });
    });
  }
};

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, FormsModule, LocationSelectorComponent],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})

export class DashboardComponent implements OnInit, OnDestroy, AfterViewInit {
  apiService = inject(ApiService);
  cdr = inject(ChangeDetectorRef);

  activeTab: string = 'summary';
  isLoading: boolean = false;
  isOwner: boolean = false;
  centers: any[] = [];
  selectedCenter: any = null;

  startDate: string = '';
  endDate: string = '';
  currentRange: string = 'thisMonth';

  // Data properties
  summaryData: any = null;
  revenuesData: any = null;
  clientsData: any = null;
  financeData: any = null;
  staffData: any = null;

  // Chart instances to destroy before re-rendering
  hasGlobalAccess: boolean = false;
  financeDataKeys: string[] = [];
  servicesProductsData: any = null;
  charts: any = {};

  selectedDrillDownMonth: string | null = null;
  drilledMonthDailyData: any[] | null = null;
  selectedDrillDownDay: string | null = null;

  selectedClientDrillDownMonth: string | null = null;

  ngOnInit() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        this.isOwner = (user.role && user.role.toLowerCase() === 'owner') || user.is_superuser === true;
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true);
      } catch (e) { }
    }

    const today = new Date();
    const y = today.getFullYear();
    const m = today.getMonth();
    const d = today.getDate();
    this.startDate = `${y}-${String(m + 1).padStart(2, '0')}-01`;
    this.endDate = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

    this.apiService.getCenters().subscribe((data: any) => {
      this.centers = Array.isArray(data) ? data : (data.results || []);
      if (!this.isOwner) {
        const u = localStorage.getItem('user');
        if (u) {
          const uObj = JSON.parse(u);
          this.selectedCenter = uObj?.center_id || null;
        }
        if (this.centers.length > 0 && !this.centers.some((c: any) => c.id == this.selectedCenter)) {
          this.selectedCenter = this.centers[0].id;
        }
      }
      this.loadTabData();
      this.cdr.detectChanges();
    });
  }

  ngAfterViewInit() { }

  ngOnDestroy(): void {
    this.destroyCharts();
  }

  setTab(tab: string) {
    this.activeTab = tab;
    this.destroyCharts();
    this.loadTabData();
  }


  setDateRange(range: string) {
    this.currentRange = range;
    const today = new Date();
    const y = today.getFullYear();
    const m = today.getMonth();
    const d = today.getDate();

    if (range === 'thisMonth') {
      this.startDate = `${y}-${String(m + 1).padStart(2, '0')}-01`;
      this.endDate = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    } else if (range === 'past6Months') {
      const past = new Date(y, m - 5, 1);
      this.startDate = `${past.getFullYear()}-${String(past.getMonth() + 1).padStart(2, '0')}-01`;
      this.endDate = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    } else if (range === 'past12Months') {
      const past = new Date(y, m - 11, 1);
      this.startDate = `${past.getFullYear()}-${String(past.getMonth() + 1).padStart(2, '0')}-01`;
      this.endDate = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    }
    this.onFilterChange();
  }

  getTotal(arr: any[], key: string) { return (arr || []).reduce((s, i) => s + (i[key] || 0), 0); }
  getBest(arr: any[], key: string) {
    if (!arr || !arr.length) return '';
    const best = (arr || []).reduce((max, item) => (item[key] || 0) > (max[key] || 0) ? item : max, arr[0]);
    return best.day || best.month || best.hour || '';
  }
  getAvg(arr: any[], key: string) {
    if (!arr || !arr.length) return 0;
    return this.getTotal(arr, key) / arr.length;
  }

  onFilterChange() {
    this.destroyCharts();
    this.loadTabData();
  }

  // --- CHART DATA AGGREGATOR ---
  // Aggregates a dictionary of { "YYYY-MM-DD": { prop1: val, prop2: val } } into monthly buckets
  aggregateToMonthly(dataObj: any): { aggregated: any, labels: string[] } {
    if (!dataObj) return { aggregated: {}, labels: [] };
    const monthlyData: any = {};
    const labelsSet = new Set<string>();

    Object.keys(dataObj).forEach(dateStr => {
      if (!dateStr || dateStr.length < 7) return;
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return;

      const monthName = date.toLocaleString('default', { month: 'short', year: '2-digit' }); // e.g., 'Jan 26'
      if (!monthlyData[monthName]) {
        monthlyData[monthName] = {};
        labelsSet.add(monthName);
      }

      const dailyMetrics = dataObj[dateStr];
      Object.keys(dailyMetrics).forEach(metricKey => {
        if (typeof dailyMetrics[metricKey] === 'object' && dailyMetrics[metricKey] !== null) {
           if (!monthlyData[monthName][metricKey]) monthlyData[monthName][metricKey] = {};
           const innerMetrics = dailyMetrics[metricKey];
           Object.keys(innerMetrics).forEach(k => {
             if (typeof innerMetrics[k] === 'number') {
               monthlyData[monthName][metricKey][k] = (monthlyData[monthName][metricKey][k] || 0) + innerMetrics[k];
             }
           });
        } else if (typeof dailyMetrics[metricKey] === 'number') {
           monthlyData[monthName][metricKey] = (monthlyData[monthName][metricKey] || 0) + dailyMetrics[metricKey];
        }
      });
    });

    const sortedLabels = Array.from(labelsSet).sort((a, b) => {
      const [m1, y1] = a.split(' ');
      const [m2, y2] = b.split(' ');
      return new Date(`${m1} 1, 20${y1}`).getTime() - new Date(`${m2} 1, 20${y2}`).getTime();
    });

    return { aggregated: monthlyData, labels: sortedLabels };
  }

  getCenterId(): number | undefined {
    return (this.selectedCenter === 'null' || !this.selectedCenter) ? undefined : parseInt(this.selectedCenter, 10);
  }

  loadTabData() {
    this.isLoading = true;
    const cid = this.getCenterId();
    const params = { center_id: cid, start_date: this.startDate, end_date: this.endDate };

    if (this.activeTab === 'summary') {
      this.apiService.get('salon_admin/api/dashboard/summary/', params).subscribe({
        next: (res) => {
          this.summaryData = res;
          this.isLoading = false;
          this.cdr.detectChanges();
          setTimeout(() => this.renderSummaryCharts(), 150);
        },
        error: () => { this.isLoading = false; this.cdr.detectChanges(); }
      });
    } else if (this.activeTab === 'revenues') {
      this.apiService.get('salon_admin/api/dashboard/revenues/', params).subscribe({
        next: (res) => {
          this.revenuesData = res;
          this.isLoading = false;
          this.cdr.detectChanges();
          setTimeout(() => this.renderRevenuesCharts(), 150);
        },
        error: () => { this.isLoading = false; this.cdr.detectChanges(); }
      });
    } else if (this.activeTab === 'clients') {
      this.apiService.get('salon_admin/api/dashboard/clients/', params).subscribe({
        next: (res) => {
          this.clientsData = res;
          this.isLoading = false;
          this.cdr.detectChanges();
          setTimeout(() => this.renderClientsCharts(), 150);
        },
        error: () => { this.isLoading = false; this.cdr.detectChanges(); }
      });
    } else if (this.activeTab === 'finance') {
      this.apiService.get('salon_admin/api/dashboard/finance/', params).subscribe({
        next: (res) => {
          this.financeData = res;
          this.financeDataKeys = Object.keys(res || {});
          this.isLoading = false;
          this.cdr.detectChanges();
          setTimeout(() => this.renderFinanceCharts(), 150);
        },
        error: () => { this.isLoading = false; this.cdr.detectChanges(); }
      });
    } else if (this.activeTab === 'services_products') {
      this.apiService.get('salon_admin/api/dashboard/services_products/', params).subscribe({
        next: (res) => {
          this.servicesProductsData = res;
          this.isLoading = false;
          this.cdr.detectChanges();
          setTimeout(() => this.renderServicesProductsCharts(), 150);
        },
        error: () => { this.isLoading = false; this.cdr.detectChanges(); }
      });
    } else if (this.activeTab === 'staff') {
      this.apiService.get('salon_admin/api/dashboard/staff/', params).subscribe({
        next: (res) => {
          this.staffData = res;
          this.isLoading = false;
          this.cdr.detectChanges();
          setTimeout(() => this.renderStaffCharts(), 150);
        },
        error: () => { this.isLoading = false; this.cdr.detectChanges(); }
      });
    }
  }

  destroyCharts() {
    Object.keys(this.charts).forEach(key => {
      if (this.charts[key]) this.charts[key].destroy();
    });
    this.charts = {};
  }

  // --- SUMMARY CHARTS ---
  renderSummaryCharts() {
    if (!this.summaryData) return;
    // Donut
    const ctxDonut = document.getElementById('revenuePieChart') as HTMLCanvasElement;
    if (ctxDonut) {
      let svcRev = 0, prodRev = 0;
      (this.summaryData.top_services || []).forEach((s: any) => svcRev += (s.revenue || 0));
      (this.summaryData.top_products || []).forEach((s: any) => prodRev += (s.revenue || 0));

      this.charts['donut'] = new Chart(ctxDonut, {
        type: 'doughnut',
        data: {
          labels: ['Services', 'Products'],
          datasets: [{ data: [svcRev, prodRev], backgroundColor: ['#0ea5e9', '#10b981'] }]
        },
        options: { responsive: true, maintainAspectRatio: false, animation: { duration: 800, easing: 'easeOutQuart' } }, plugins: [dataLabelsPlugin]
      });
    }

    // Bar
    const ctxBar = document.getElementById('summaryLineChart') as HTMLCanvasElement;
    if (ctxBar) {
      const labels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const data = this.summaryData.weekday_counts || [0, 0, 0, 0, 0, 0, 0];
      this.charts['sumBar'] = new Chart(ctxBar, {
        type: 'line',
        data: {
          labels,
          datasets: [{ 
            label: 'Invoice Count', 
            data, 
            borderColor: '#6366f1',
            backgroundColor: (context: any) => {
              const canvasCtx = context.chart.ctx;
              const grad = canvasCtx.createLinearGradient(0, 0, 0, 300);
              grad.addColorStop(0, '#6366f166');
              grad.addColorStop(1, '#6366f100');
              return grad;
            },
            fill: true,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#6366f1'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, animation: { duration: 800, easing: 'easeOutQuart' }, scales: { x: { offset: labels.length === 1 } } }, plugins: [dataLabelsPlugin]
      });
    }
  }

  // --- DRILL-DOWN LOGIC ---
  resetDrillDownMonth() {
    this.selectedDrillDownMonth = null;
    this.drilledMonthDailyData = null;
    this.selectedDrillDownDay = null; // cascade reset
    // Re-render original data
    if (this.revenuesData) {
      this.renderRevenuesCharts(this.revenuesData.daily, this.revenuesData.hourly);
    }
    this.cdr.detectChanges();
  }

  resetDrillDownDay() {
    this.selectedDrillDownDay = null;
    // We might still be drilled down into a month, so re-render with the month's hourly data
    if (this.selectedDrillDownMonth) {
      // Re-fetch the month's data to get its hourly aggregation, or we can just fetch the month again
      const [mon, yy] = this.selectedDrillDownMonth.split('-');
      const y = yy;
      const mNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const m = mNames.indexOf(mon) + 1;
      const sd = `${y}-${String(m).padStart(2, '0')}-01`;
      const ed = new Date(parseInt(y), m, 0);
      const edStr = `${y}-${String(m).padStart(2, '0')}-${String(ed.getDate()).padStart(2, '0')}`;
      this.fetchDrillDownData('month', sd, edStr);
    } else {
      if (this.revenuesData) {
        this.renderRevenuesCharts(this.revenuesData.daily, this.revenuesData.hourly);
      }
    }
    this.cdr.detectChanges();
  }

  fetchDrillDownData(level: 'month'|'day', sd: string, ed: string) {
    const cid = this.getCenterId();
    const params = { center_id: cid, start_date: sd, end_date: ed };
    this.apiService.get('salon_admin/api/dashboard/revenues/', params).subscribe({
      next: (res) => {
        if (level === 'month') {
          // Keep original monthly data, but replace daily and hourly
          this.drilledMonthDailyData = res.daily;
          this.renderRevenuesCharts(res.daily, res.hourly);
        } else if (level === 'day') {
          // Keep whatever daily data is currently showing, but replace hourly
          // But actually renderRevenuesCharts uses the class properties, so we pass overrides
          this.renderRevenuesCharts(this.drilledMonthDailyData, res.hourly);
        }
        this.cdr.detectChanges();
      },
      error: () => {}
    });
  }

  resetClientDrillDownMonth() {
    this.selectedClientDrillDownMonth = null;
    this.renderClientsCharts();
    this.cdr.detectChanges();
  }

  fetchClientDrillDownData(level: 'month', sd: string, ed: string) {
    const cid = this.getCenterId();
    const params = { center_id: cid, start_date: sd, end_date: ed };
    this.apiService.get('salon_admin/api/dashboard/clients/', params).subscribe({
      next: (res) => {
        this.renderClientsCharts(res.daily_footfall);
        this.cdr.detectChanges();
      },
      error: () => {}
    });
  }

  // --- REVENUES CHARTS ---
  renderRevenuesCharts(dailyDataOverride: any = null, hourlyDataOverride: any = null) {
    if (!this.revenuesData) return;
    if (this.charts['revMonthlyChart']) this.charts['revMonthlyChart'].destroy();
    if (this.charts['revDailyChart']) this.charts['revDailyChart'].destroy();
    if (this.charts['revHourlyChart']) this.charts['revHourlyChart'].destroy();

    const renderLine = (id: string, labels: any[], data: any[], color: string, label: string, onClickHandler?: (e: any, elements: any[], chart: any) => void) => {
      const ctx = document.getElementById(id) as HTMLCanvasElement;
      if (!ctx) return;
      this.charts[id] = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{ 
            label, 
            data, 
            borderColor: color,
            backgroundColor: (context: any) => {
              const canvasCtx = context.chart.ctx;
              const grad = canvasCtx.createLinearGradient(0, 0, 0, 350);
              grad.addColorStop(0, color + '66');
              grad.addColorStop(1, color + '00');
              return grad;
            },
            fill: true,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: color,
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6
          }]
        },
        options: { 
          responsive: true, 
          maintainAspectRatio: false, 
          animation: { duration: 800, easing: 'easeOutQuart' },
          scales: { x: { offset: labels.length === 1 } },
          onClick: onClickHandler ? (e, elements, chart) => onClickHandler(e, elements, chart) : undefined,
          onHover: onClickHandler ? (e, elements) => {
            if (e.native && e.native.target) {
              (e.native.target as HTMLElement).style.cursor = elements.length ? 'pointer' : 'default';
            }
          } : undefined
        }, 
        plugins: [dataLabelsPlugin]
      });
    };

    const monthlyLabels = (this.revenuesData.monthly || []).map((d: any) => d.month);
    renderLine('revMonthlyChart', monthlyLabels, (this.revenuesData.monthly || []).map((d: any) => d.revenue), '#f59e0b', 'Monthly Revenue', (e, elements, chart) => {
      if (!elements || !elements.length) return;
      const index = elements[0].index;
      const monthStr = monthlyLabels[index]; // e.g. "Mar-2026"
      this.selectedDrillDownMonth = monthStr;
      
      const [mon, yy] = monthStr.split('-');
      const y = yy;
      const mNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const m = mNames.indexOf(mon) + 1;
      const sd = `${y}-${String(m).padStart(2, '0')}-01`;
      const ed = new Date(parseInt(y), m, 0);
      const edStr = `${y}-${String(m).padStart(2, '0')}-${String(ed.getDate()).padStart(2, '0')}`;
      this.fetchDrillDownData('month', sd, edStr);
      this.cdr.detectChanges();
    });

    let dailyData = dailyDataOverride || this.revenuesData.daily || [];
    let dailyTitle = 'Daily Revenue';
    
    // Only aggregate if we are not drilled down, AND range is 6m/12m
    if (!this.selectedDrillDownMonth && (this.currentRange === 'past6Months' || this.currentRange === 'past12Months')) {
      const weeklyMap: any = {};
      const weeklyOrder: string[] = [];
      
      dailyData.forEach((d: any) => {
        const date = new Date(d.day);
        if (isNaN(date.getTime())) return;
        
        // Find Monday of the week
        const dayOfWeek = date.getDay();
        const diff = date.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
        const weekStart = new Date(date.setDate(diff));
        const weekStr = weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        if (weeklyMap[weekStr] === undefined) {
          weeklyMap[weekStr] = 0;
          weeklyOrder.push(weekStr);
        }
        weeklyMap[weekStr] += (d.revenue || 0);
      });
      
      dailyData = weeklyOrder.map(k => ({ day: `Week of ${k}`, revenue: weeklyMap[k], originalDate: null }));
      dailyTitle = 'Weekly Revenue';
    }

    const dailyLabels = dailyData.map((d: any) => d.day);
    renderLine('revDailyChart', dailyLabels, dailyData.map((d: any) => d.revenue), '#10b981', dailyTitle, (e, elements, chart) => {
      if (!elements || !elements.length) return;
      const index = elements[0].index;
      const dayStr = dailyLabels[index]; 
      
      if (dayStr.startsWith('Week of')) {
        // Can't easily drill down a week directly to a day without calculating dates
        return; 
      }
      this.selectedDrillDownDay = dayStr;
      this.fetchDrillDownData('day', dayStr, dayStr);
      this.cdr.detectChanges();
    });

    const hourlyData = hourlyDataOverride || this.revenuesData.hourly || [];
    renderLine('revHourlyChart', hourlyData.map((d: any) => d.hour), hourlyData.map((d: any) => d.revenue), '#3b82f6', 'Hourly Revenue');
  }

  // --- CLIENTS CHARTS ---
  renderClientsCharts(dailyDataOverride?: any) {
    if (!this.clientsData || !this.clientsData.trends) return;

    let trendData = this.clientsData.trends;
    let labels = Object.keys(trendData);
    
    if (this.currentRange === 'past6Months' || this.currentRange === 'past12Months') {
      const agg = this.aggregateToMonthly(this.clientsData.trends);
      trendData = agg.aggregated;
      labels = agg.labels;
    }

    const ctxBreakdown = document.getElementById('clientBreakdownChart') as HTMLCanvasElement;
    if (ctxBreakdown && this.clientsData.monthly_breakdown) {
      const breakdownData = this.clientsData.monthly_breakdown;
      const bLabels = Object.keys(breakdownData);
      
      const newClients = bLabels.map(l => breakdownData[l]?.new || 0);
      const repeatClients = bLabels.map(l => breakdownData[l]?.repeat || 0);
      const memberInvoices = bLabels.map(l => breakdownData[l]?.member || 0);
      const nonMemberInvoices = bLabels.map(l => breakdownData[l]?.non_member || 0);

      this.charts['breakdown'] = new Chart(ctxBreakdown, {
        type: 'line',
        data: {
          labels: bLabels,
          datasets: [
            { 
              label: 'New Clients', 
              data: newClients, 
              borderColor: '#0ea5e9', 
              backgroundColor: (context: any) => { const grad = context.chart.ctx.createLinearGradient(0, 0, 0, 300); grad.addColorStop(0, '#0ea5e966'); grad.addColorStop(1, '#0ea5e900'); return grad; },
              fill: true,
              pointBackgroundColor: '#ffffff'
            },
            { 
              label: 'Repeat Clients', 
              data: repeatClients, 
              borderColor: '#6366f1', 
              backgroundColor: (context: any) => { const grad = context.chart.ctx.createLinearGradient(0, 0, 0, 300); grad.addColorStop(0, '#6366f166'); grad.addColorStop(1, '#6366f100'); return grad; },
              fill: true,
              pointBackgroundColor: '#ffffff'
            },
            { 
              label: 'Members Invoices', 
              data: memberInvoices, 
              borderColor: '#10b981', 
              backgroundColor: (context: any) => { const grad = context.chart.ctx.createLinearGradient(0, 0, 0, 300); grad.addColorStop(0, '#10b98166'); grad.addColorStop(1, '#10b98100'); return grad; },
              fill: true,
              pointBackgroundColor: '#ffffff'
            },
            { 
              label: 'Non members Invoices', 
              data: nonMemberInvoices, 
              borderColor: '#f97316', 
              backgroundColor: (context: any) => { const grad = context.chart.ctx.createLinearGradient(0, 0, 0, 300); grad.addColorStop(0, '#f9731666'); grad.addColorStop(1, '#f9731600'); return grad; },
              fill: true,
              pointBackgroundColor: '#ffffff'
            }
          ]
        },
        options: { 
          responsive: true, 
          maintainAspectRatio: false, 
          animation: { duration: 800, easing: 'easeOutQuart' },
          plugins: { legend: { display: true, position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, font: { size: 11 } } } },
          layout: { padding: { top: 30 } },
          scales: { x: { offset: bLabels.length === 1 } },
          onClick: (e: any, elements: any[], chart: any) => {
            if (!elements || elements.length === 0) return;
            const index = elements[0].index;
            const monthStr = bLabels[index]; // e.g. "Mar-2026"
            this.selectedClientDrillDownMonth = monthStr;
            
            const [mon, yy] = monthStr.split('-');
            const y = yy;
            const mNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const m = mNames.indexOf(mon) + 1;
            const sd = `${y}-${String(m).padStart(2, '0')}-01`;
            const ed = new Date(parseInt(y), m, 0);
            const edStr = `${y}-${String(m).padStart(2, '0')}-${String(ed.getDate()).padStart(2, '0')}`;
            
            this.fetchClientDrillDownData('month', sd, edStr);
            this.cdr.detectChanges();
          }
        },
        plugins: [dataLabelsPlugin]
      });
    }

    const renderCombo = (id: string, prop: string, color: string) => {
      const ctx = document.getElementById(id) as HTMLCanvasElement;
      if (!ctx) return;
      const newCounts = labels.map(l => trendData[l]?.[prop]?.new || 0);
      const repeatCounts = labels.map(l => trendData[l]?.[prop]?.repeat || 0);
      const avg = labels.map(l => {
        const c = trendData[l]?.[prop]?.count || 0;
        const r = trendData[l]?.[prop]?.revenue || 0;
        return c > 0 ? parseFloat((r / c).toFixed(2)) : 0;
      });

      this.charts[id] = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            { 
              type: 'line', 
              label: 'New Clients', 
              data: newCounts, 
              borderColor: '#0ea5e9', 
              backgroundColor: (context: any) => { const grad = context.chart.ctx.createLinearGradient(0, 0, 0, 300); grad.addColorStop(0, '#0ea5e966'); grad.addColorStop(1, '#0ea5e900'); return grad; },
              fill: true,
              pointBackgroundColor: '#ffffff',
              yAxisID: 'y' 
            } as any,
            { 
              type: 'line', 
              label: 'Repeat Clients', 
              data: repeatCounts, 
              borderColor: '#6366f1', 
              backgroundColor: (context: any) => { const grad = context.chart.ctx.createLinearGradient(0, 0, 0, 300); grad.addColorStop(0, '#6366f166'); grad.addColorStop(1, '#6366f100'); return grad; },
              fill: true,
              pointBackgroundColor: '#ffffff',
              yAxisID: 'y' 
            } as any,
            { 
              type: 'line', 
              label: 'Avg Spend (Right Axes)', 
              data: avg, 
              borderColor: '#10b981', 
              pointBackgroundColor: '#ffffff', 
              yAxisID: 'y1' 
            } as any
          ]
        },
        options: {
          responsive: true, maintainAspectRatio: false, animation: { duration: 800, easing: 'easeOutQuart' },
          plugins: { legend: { display: true, position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, font: { size: 11 } } } },
          layout: { padding: { top: 30 } },
          scales: {
            x: { offset: labels.length === 1 },
            y: { type: 'linear', position: 'left', title: { display: true, text: 'Clients', color: '#0ea5e9' } },
            y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Average Spend', color: '#10b981' } }
          }
        },
        plugins: [dataLabelsPlugin]
      });
    };

    renderCombo('femaleTrendChart', 'female', '#ec4899');
    renderCombo('maleTrendChart', 'male', '#0ea5e9');
    renderCombo('unknownTrendChart', 'unknown', '#8b5cf6');

    const ctxDaily = document.getElementById('clientDailyChart') as HTMLCanvasElement;
    if (ctxDaily && this.clientsData.daily_footfall) {
      let dailyData = dailyDataOverride || this.clientsData.daily_footfall;
      let dailyTitle = 'Daily Client Footfall';

      if (!this.selectedClientDrillDownMonth && (this.currentRange === 'past6Months' || this.currentRange === 'past12Months')) {
        const weeklyMap: any = {};
        const weeklyOrder: string[] = [];
        
        dailyData.forEach((d: any) => {
          // Parse '%d-%m-%Y' or '%Y-%m-%d'
          // We will update backend to return '%Y-%m-%d' to match JS easily
          const date = new Date(d.day);
          if (isNaN(date.getTime())) return;
          
          const dayOfWeek = date.getDay();
          const diff = date.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
          const weekStart = new Date(date.setDate(diff));
          const weekStr = weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
          
          if (weeklyMap[weekStr] === undefined) {
            weeklyMap[weekStr] = 0;
            weeklyOrder.push(weekStr);
          }
          weeklyMap[weekStr] += (d.count || 0);
        });
        
        dailyData = weeklyOrder.map(k => ({ day: `Week of ${k}`, count: weeklyMap[k] }));
        dailyTitle = 'Weekly Client Footfall';
      }

      const dLabels = dailyData.map((d: any) => d.day);
      const dCounts = dailyData.map((d: any) => d.count);
      
      this.charts['clientDaily'] = new Chart(ctxDaily, {
        type: 'line',
        data: {
          labels: dLabels,
          datasets: [{ 
            label: dailyTitle, 
            data: dCounts, 
            borderColor: '#3b82f6',
            backgroundColor: (context: any) => { const grad = context.chart.ctx.createLinearGradient(0, 0, 0, 300); grad.addColorStop(0, '#3b82f666'); grad.addColorStop(1, '#3b82f600'); return grad; },
            fill: true,
            pointBackgroundColor: '#ffffff'
          }]
        },
        options: { 
          responsive: true, 
          maintainAspectRatio: false, 
          animation: { duration: 800, easing: 'easeOutQuart' },
          plugins: { legend: { display: false } },
          layout: { padding: { top: 30 } },
          scales: { x: { offset: dLabels.length === 1 } }
        },
        plugins: [dataLabelsPlugin]
      });
    }
  }

  // --- FINANCE CHARTS ---
  renderFinanceCharts() {
    if (!this.financeData) return;
    
    let currentFinanceData = this.financeData;
    let months = Object.keys(currentFinanceData);

    if (this.currentRange === 'past6Months' || this.currentRange === 'past12Months') {
      const agg = this.aggregateToMonthly(this.financeData);
      currentFinanceData = agg.aggregated;
      months = agg.labels;
    }

    const makeFinBarLine = (id: string, labels: string[], dataKey: string, barColor: string) => {
      try {
        const el = document.getElementById(id) as HTMLCanvasElement;
        if (!el) return;
        const c2d = el.getContext('2d')!;
        const grad = c2d.createLinearGradient(0, 0, 0, 250);
        grad.addColorStop(0, barColor + 'ff');
        grad.addColorStop(1, barColor + '00');

        const revData = labels.map(m => currentFinanceData[m]?.[dataKey]?.revenue || 0);
        const countData = labels.map(m => currentFinanceData[m]?.[dataKey]?.count || 0);

        this.charts[id] = new Chart(el, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [
              {
                type: 'line' as any,
                label: 'Revenue',
                data: revData,
                borderColor: barColor,
                backgroundColor: grad,
                fill: true,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: barColor,
                yAxisID: 'y'
              },
              {
                type: 'line' as any,
                label: 'Counts',
                data: countData,
                borderColor: '#3b82f6',
                backgroundColor: '#3b82f6',
                pointBackgroundColor: '#60a5fa',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                borderWidth: 2,
                yAxisID: 'y1'
              }
            ]
          },
          options: {
            responsive: true, animation: { duration: 800, easing: 'easeOutQuart' },
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: {
                offset: labels.length === 1,
                grid: { display: false },
                ticks: { color: '#6b7280', font: { size: 10 } }
              },
              y: {
                type: 'linear',
                display: true,
                position: 'left',
                title: { display: true, text: 'Revenue', color: '#9ca3af', font: { size: 10 } },
                ticks: {
                  callback: (v: any) => (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v),
                  color: '#9ca3af', font: { size: 10 }
                },
                grid: { display: true, color: 'rgba(0,0,0,0.035)' }
              },
              y1: {
                type: 'linear',
                display: true,
                position: 'right',
                title: { display: true, text: 'Counts', color: '#9ca3af', font: { size: 10 } },
                grid: { drawOnChartArea: false },
                ticks: {
                  color: '#9ca3af', font: { size: 10 },
                  stepSize: 1
                }
              }
            }
          }
        });
      } catch (e) { console.error('Error rendering', id, e); }
    };

    makeFinBarLine('finServicesChart', months, 'services', '#0d5d73');
    makeFinBarLine('finMembershipsChart', months, 'memberships', '#a5d6e9');
    makeFinBarLine('finProductsChart', months, 'products', '#86efac');
    makeFinBarLine('finPackagesChart', months, 'packages', '#6366f1');
    makeFinBarLine('finValueCardsChart', months, 'value_cards', '#f59e0b');
    makeFinBarLine('finAdvancesChart', months, 'advances', '#6b7280');
  }

  // --- STAFF CHARTS ---
  renderStaffCharts() {
    if (!this.staffData) return;
    const ctxMonth = document.getElementById('staffThisMonthChart') as HTMLCanvasElement;
    if (ctxMonth) {
      const labels = (this.staffData.table || []).map((s: any) => s.name).slice(0, 10);
      const data = (this.staffData.table || []).map((s: any) => s.revenue || 0).slice(0, 10);
      this.charts['staffMonth'] = new Chart(ctxMonth, {
        type: 'line',
        data: { labels, datasets: [{ 
          label: 'Revenue', 
          data, 
          borderColor: '#8b5cf6',
          backgroundColor: (context: any) => {
            const canvasCtx = context.chart.ctx;
            const grad = canvasCtx.createLinearGradient(0, 0, 0, 300);
            grad.addColorStop(0, '#8b5cf666');
            grad.addColorStop(1, '#8b5cf600');
            return grad;
          },
          fill: true,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#8b5cf6'
        }] },
        options: { responsive: true, maintainAspectRatio: false, animation: { duration: 800, easing: 'easeOutQuart' }, scales: { x: { offset: labels.length === 1 } } }, plugins: [dataLabelsPlugin]
      });
    }

    const ctx6 = document.getElementById('staffSixMonthsChart') as HTMLCanvasElement;
    if (ctx6) {
      const labels = (this.staffData.trends || []).map((t: any) => t.month);
      const data = (this.staffData.trends || []).map((t: any) => t.revenue || 0);
      this.charts['staff6'] = new Chart(ctx6, {
        type: 'line',
        data: { labels, datasets: [{ 
          label: 'Total Staff Revenue', 
          data, 
          borderColor: '#10b981',
          backgroundColor: (context: any) => {
            const canvasCtx = context.chart.ctx;
            const grad = canvasCtx.createLinearGradient(0, 0, 0, 300);
            grad.addColorStop(0, '#10b98166');
            grad.addColorStop(1, '#10b98100');
            return grad;
          },
          tension: 0.4, 
          fill: true,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#10b981'
        }] },
        options: { responsive: true, maintainAspectRatio: false, animation: { duration: 800, easing: 'easeOutQuart' }, scales: { x: { offset: labels.length === 1 } } }, plugins: [dataLabelsPlugin]
      });
    }
  }
  renderServicesProductsCharts() {
    if (!this.servicesProductsData) return;

    // Service Category Chart
    const ctxSvc = document.getElementById('serviceCategoryChart') as HTMLCanvasElement;
    if (ctxSvc && this.servicesProductsData.services?.length) {
      const topServices = this.servicesProductsData.services.slice(0, 15);
      const labels = topServices.map((s: any) => s.name);
      const data = topServices.map((s: any) => s.revenue);
      this.charts['svcCat'] = new Chart(ctxSvc, {
        type: 'line',
        data: {
          labels,
          datasets: [{ 
            label: 'Revenue', 
            data, 
            borderColor: '#0ea5e9',
            backgroundColor: (context: any) => {
              const canvasCtx = context.chart.ctx;
              const grad = canvasCtx.createLinearGradient(0, 0, 0, 300);
              grad.addColorStop(0, '#0ea5e966');
              grad.addColorStop(1, '#0ea5e900');
              return grad;
            },
            fill: true,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#0ea5e9'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, animation: { duration: 800, easing: 'easeOutQuart' }, scales: { x: { offset: labels.length === 1 } } }, plugins: [dataLabelsPlugin]
      });
    }

    // Product Category Chart
    const ctxProd = document.getElementById('productCategoryChart') as HTMLCanvasElement;
    if (ctxProd && this.servicesProductsData.products?.length) {
      const topProducts = this.servicesProductsData.products.slice(0, 15);
      const labels = topProducts.map((p: any) => p.name);
      const data = topProducts.map((p: any) => p.revenue);
      this.charts['prodCat'] = new Chart(ctxProd, {
        type: 'line',
        data: {
          labels,
          datasets: [{ 
            label: 'Revenue', 
            data, 
            borderColor: '#10b981',
            backgroundColor: (context: any) => {
              const canvasCtx = context.chart.ctx;
              const grad = canvasCtx.createLinearGradient(0, 0, 0, 300);
              grad.addColorStop(0, '#10b98166');
              grad.addColorStop(1, '#10b98100');
              return grad;
            },
            fill: true,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#10b981'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, animation: { duration: 800, easing: 'easeOutQuart' } }, plugins: [dataLabelsPlugin]
      });
    }
  }
}
