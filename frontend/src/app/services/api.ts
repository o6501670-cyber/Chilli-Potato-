import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  public baseUrl = environment.apiUrl;


  // Generic methods
  get(path: string, params?: Record<string, any>, options?: any): Observable<any> {
    let url = `${this.baseUrl}/${path}`;
    if (params) {
      const queryParts: string[] = [];
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          queryParts.push(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
        }
      });
      if (queryParts.length > 0) {
        url += (url.includes('?') ? '&' : '?') + queryParts.join('&');
      }
    }
    return this.http.get<any>(url, options);
  }

  post(path: string, body: any, options?: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/${path}`, body, options);
  }

  put(path: string, body: any): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/${path}`, body);
  }

  patch(path: string, body: any): Observable<any> {
    return this.http.patch<any>(`${this.baseUrl}/${path}`, body);
  }

  delete(path: string): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/${path}`);
  }

  // Chat
  getUnreadChatCount(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/accounts/api/chat/unread/`);
  }

  // Centers
  getCenters(withRevenue = false): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/salon_admin/api/centers/?${withRevenue ? '&with_revenue=true' : ''}`);
  }

  createCenter(data: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/salon_admin/api/centers/`, data);
  }

  updateCenter(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/salon_admin/api/centers/${id}/`, data);
  }

  bulkImportCenters(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.baseUrl}/salon_admin/api/centers/bulk-import/`, formData);
  }

  downloadCentersTemplate(): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/salon_admin/api/centers/bulk-import-template/`, { responseType: 'blob' });
  }

  // Users
  getUsers(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/accounts/api/users/`);
  }

  getClients(q?: string, centerId?: number, page?: number): Observable<any> {
    let url = `${this.baseUrl}/clients/api/clients/`;
    if (q) url += `${url.includes('?') ? '&' : '?'}q=${encodeURIComponent(q)}`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (page) url += `${url.includes('?') ? '&' : '?'}page=${page}`;
    return this.http.get<any>(url);
  }

  createClient(data: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/clients/api/clients/`, data);
  }

  updateClient(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/clients/api/clients/${id}/`, data);
  }

  getClientProfile(id: number): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/clients/api/clients/${id}/profile/`);
  }

  createUser(data: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/accounts/api/users/`, data);
  }

  updateUser(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/accounts/api/users/${id}/`, data);
  }

  // Roles & Designations
  getRoles(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/salon_admin/api/roles/`);
  }

  createRole(data: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/salon_admin/api/roles/`, data);
  }

  updateRole(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/salon_admin/api/roles/${id}/`, data);
  }

  deleteRole(id: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/salon_admin/api/roles/${id}/`);
  }

  getDesignations(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/staff/api/designations/`);
  }

  createDesignation(data: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/staff/api/designations/`, data);
  }

  updateDesignation(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/staff/api/designations/${id}/`, data);
  }

  deleteDesignation(id: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/staff/api/designations/${id}/`);
  }

  // --- Inventory ---
  getProducts(centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/inventory/api/products/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  getLowStockAlerts(centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/inventory/api/low_stock/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  createProduct(product: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/inventory/api/products/`, product);
  }

  updateProduct(id: number, product: any, updateAllCenters: boolean = false): Observable<any> {
    let url = `${this.baseUrl}/inventory/api/products/${id}/`;
    if (updateAllCenters) url += `?update_all_centers=true`;
    return this.http.put(url, product);
  }

  deleteProduct(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/inventory/api/products/${id}/`);
  }

  downloadProductsTemplate(): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/inventory/api/products/bulk_upload_template/`, { responseType: 'blob' });
  }

  createProductLot(lot: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/inventory/api/lots/`, lot);
  }

  updateProductLot(id: number, lot: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/inventory/api/lots/${id}/`, lot);
  }

  deleteProductLot(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/inventory/api/lots/${id}/`);
  }

  getVendors(centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/inventory/api/vendors/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  createVendor(vendor: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/inventory/api/vendors/`, vendor);
  }

  updateVendor(id: number, vendor: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/inventory/api/vendors/${id}/`, vendor);
  }

  deleteVendor(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/inventory/api/vendors/${id}/`);
  }

  downloadVendorsTemplate(): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/inventory/api/vendors/bulk_upload_template/`, { responseType: 'blob' });
  }

  getPurchaseOrders(centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/inventory/api/purchase-orders/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  createPurchaseOrder(po: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/inventory/api/purchase-orders/`, po);
  }

  updatePurchaseOrder(id: number, po: any): Observable<any> {
    return this.http.patch(`${this.baseUrl}/inventory/api/purchase-orders/${id}/`, po);
  }

  deletePurchaseOrder(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/inventory/api/purchase-orders/${id}/`);
  }

  inventoryCheckout(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/inventory/api/products/checkout/`, data);
  }

  inventoryAudit(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/inventory/api/products/audit/`, data);
  }

  getStockHistory(date: string, centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/inventory/api/products/stock_history/?date=${date}`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  getStockTransactions(centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/inventory/api/stock-transactions/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  // --- Marketing ---
  getWhatsAppMessages(centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/marketing/api/whatsapp/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  sendWhatsAppCampaign(centerId: number | 'all', message: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/marketing/api/whatsapp/send_campaign/`, { center_id: centerId, message: message });
  }


  getPromotionUsage(startDate?: string, endDate?: string): Observable<any[]> {
    let url = `${this.baseUrl}/marketing/api/promotions/usage_report/`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any[]>(url);
  }

  // Marketing - Promotions
  getPromotions(centerId?: any, showInactive: boolean = false, showExpired: boolean = false) { 
    let url = `${this.baseUrl}/marketing/api/promotions/`;
    if (centerId !== undefined && centerId !== null && centerId !== 'null') url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (showExpired) url += `${url.includes('?') ? '&' : '?'}show_expired=true`;
    if (showInactive) url += `${url.includes('?') ? '&' : '?'}show_inactive=true`;
    return this.http.get<any[]>(url); 
  }
  createPromotion(data: any) { return this.http.post(`${this.baseUrl}/marketing/api/promotions/`, data); }
  updatePromotion(id: number, data: any) { return this.http.patch(`${this.baseUrl}/marketing/api/promotions/${id}/`, data); }
  togglePromotion(id: number) { return this.http.patch(`${this.baseUrl}/marketing/api/promotions/${id}/toggle-status/`, {}); }
  deletePromotion(id: number) { return this.http.delete(`${this.baseUrl}/marketing/api/promotions/${id}/`); }

  // Marketing - Value Cards
  getValueCards(centerId?: any, showInactive: boolean = false) { 
    let url = `${this.baseUrl}/marketing/api/cards/`;
    if (centerId !== undefined && centerId !== null && centerId !== 'null') url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (showInactive) url += `${url.includes('?') ? '&' : '?'}show_inactive=true`;
    return this.http.get<any[]>(url); 
  }
  createValueCard(data: any) { return this.http.post(`${this.baseUrl}/marketing/api/cards/`, data); }
  updateValueCard(id: number, data: any) { return this.http.patch(`${this.baseUrl}/marketing/api/cards/${id}/`, data); }
  toggleValueCard(id: number) { return this.http.patch(`${this.baseUrl}/marketing/api/cards/${id}/toggle-status/`, {}); }
  deleteValueCard(id: number) { return this.http.delete(`${this.baseUrl}/marketing/api/cards/${id}/`); }

  // Marketing - Memberships
  getMemberships(centerId?: any, showInactive: boolean = false) { 
    let url = `${this.baseUrl}/marketing/api/memberships/`;
    if (centerId !== undefined && centerId !== null && centerId !== 'null') url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (showInactive) url += `${url.includes('?') ? '&' : '?'}show_inactive=true`;
    return this.http.get<any[]>(url); 
  }
  createMembership(data: any) { return this.http.post(`${this.baseUrl}/marketing/api/memberships/`, data); }
  updateMembership(id: number, data: any) { return this.http.patch(`${this.baseUrl}/marketing/api/memberships/${id}/`, data); }
  toggleMembership(id: number) { return this.http.patch(`${this.baseUrl}/marketing/api/memberships/${id}/toggle-status/`, {}); }
  deleteMembership(id: number) { return this.http.delete(`${this.baseUrl}/marketing/api/memberships/${id}/`); }

  // Marketing - Packages
  getPackages(centerId?: any, showInactive: boolean = false) { 
    let url = `${this.baseUrl}/marketing/api/packages/`;
    if (centerId !== undefined && centerId !== null && centerId !== 'null') url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (showInactive) url += `${url.includes('?') ? '&' : '?'}show_inactive=true`;
    return this.http.get<any[]>(url); 
  }
  createPackage(data: any) { return this.http.post(`${this.baseUrl}/marketing/api/packages/`, data); }
  updatePackage(id: number, data: any) { return this.http.patch(`${this.baseUrl}/marketing/api/packages/${id}/`, data); }
  togglePackage(id: number) { return this.http.patch(`${this.baseUrl}/marketing/api/packages/${id}/toggle-status/`, {}); }
  deletePackage(id: number) { return this.http.delete(`${this.baseUrl}/marketing/api/packages/${id}/`); }

  // Services
  getServices(centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/services/api/master/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  overrideCenterService(centerId: number, serviceId: number, price: any, isActive: boolean = true): Observable<any> {
    const payload: any = { center_id: centerId, service_id: serviceId, price: price, is_active: isActive };
    return this.http.post(`${this.baseUrl}/services/api/center/override/`, payload);
  }

  createService(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/services/api/master/`, data);
  }

  updateService(id: number, data: any, centerId?: number | null): Observable<any> {
    let url = `${this.baseUrl}/services/api/master/${id}/`;
    if (centerId) url += `?center_id=${centerId}`;
    return this.http.put(url, data);
  }

  deleteService(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/services/api/master/${id}/`);
  }


  // --- Staff ---

  getStaffMembers(centerId?: number, includeInactive: boolean = false): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/members/?include_inactive=${includeInactive}`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }


  // --- Finance Export ---
  exportFinance(centerId: number | null, startDate: string, endDate: string): Observable<Blob> {
    let url = `${this.baseUrl}/finance/api/export/?start_date=${startDate}&end_date=${endDate}&type=detailed`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get(url, { responseType: 'blob' });
  }

  getStaffActivityFeed(centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/members/activity_feed/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  createStaffMember(staff: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/staff/api/members/`, staff);
  }

  updateStaffMember(id: number, staff: any): Observable<any> {
    return this.http.patch(`${this.baseUrl}/staff/api/members/${id}/`, staff);
  }

  uploadStaffImage(id: number, formData: FormData): Observable<any> {
    return this.http.patch(`${this.baseUrl}/staff/api/members/${id}/`, formData);
  }

  deleteStaffMember(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/staff/api/members/${id}/`);
  }

  downloadStaffTemplate(): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/staff/api/members/bulk_upload_template/`, { responseType: 'blob' });
  }

  getServiceLogs(staffId?: number, startDate?: string, endDate?: string): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/logs/`;
    if (staffId) url += `${url.includes('?') ? '&' : '?'}staff_id=${staffId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any[]>(url);
  }

  createServiceLog(log: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/staff/api/logs/`, log);
  }

  getServiceUsageReport(centerId?: number, startDate?: string, endDate?: string): Observable<any> {
    let url = `${this.baseUrl}/staff/api/reports/usage/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getStaffRevenueReport(centerId?: number, startDate?: string, endDate?: string): Observable<any> {
    let url = `${this.baseUrl}/staff/api/reports/revenue/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getStaffConsumptions(staffId?: number, startDate?: string, endDate?: string): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/consumptions/`;
    if (staffId) url += `${url.includes('?') ? '&' : '?'}staff_id=${staffId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any[]>(url);
  }

  createStaffConsumption(log: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/staff/api/consumptions/`, log);
  }

  getStaffConsumptionReport(centerId?: number, startDate?: string, endDate?: string): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/reports/consumption/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate && endDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}&end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  // Staff Transfers
  getStaffTransfers(staffId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/transfers/`;
    if (staffId) url += `${url.includes('?') ? '&' : '?'}staff_id=${staffId}`;
    return this.http.get<any[]>(url);
  }
  createStaffTransfer(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/staff/api/transfers/`, data);
  }
  updateStaffTransfer(id: number, data: any): Observable<any> {
    return this.http.patch(`${this.baseUrl}/staff/api/transfers/${id}/`, data);
  }

  getPayrolls(staffId?: number, centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/payrolls/`;
    if (staffId) url += `${url.includes('?') ? '&' : '?'}staff_id=${staffId}`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  lockPayroll(id: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/staff/api/payrolls/${id}/lock/`, {});
  }

  markPayrollPaid(id: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/staff/api/payrolls/${id}/mark_paid/`, {});
  }

  // Staff Tool Tracker
  getStaffTools(staffId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/tools/`;
    if (staffId) url += `${url.includes('?') ? '&' : '?'}staff_id=${staffId}`;
    return this.http.get<any[]>(url);
  }
  createStaffTool(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/staff/api/tools/`, data);
  }
  updateStaffTool(id: number, data: any): Observable<any> {
    return this.http.patch(`${this.baseUrl}/staff/api/tools/${id}/`, data);
  }

  // --- Billing ---
  getInvoices(clientId?: number, centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/billing/invoices/`;
    if (clientId) url += `${url.includes('?') ? '&' : '?'}client_id=${clientId}`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  getServiceLogsByClient(clientName: string): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/logs/?client_name=${encodeURIComponent(clientName)}`;
    return this.http.get<any[]>(url);
  }

  createInvoice(invoice: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/billing/invoices/`, invoice);
  }

  updateInvoice(id: number, invoice: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/billing/invoices/${id}/`, invoice);
  }

  deleteInvoice(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/billing/invoices/${id}/`);
  }

  payInvoice(id: number, amount: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/billing/invoices/${id}/pay/`, { amount });
  }

  createAdvance(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/billing/advances/`, data);
  }

  getAdvances(clientId?: number, centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/billing/advances/`;
    if (clientId) url += `${url.includes('?') ? '&' : '?'}client_id=${clientId}`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  // --- Appointments ---
  getAppointments(centerId?: number, date?: string, clientPhone?: string): Observable<any[]> {
    let url = `${this.baseUrl}/appointments/api/appointments/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (date) url += `${url.includes('?') ? '&' : '?'}date=${date}`;
    if (clientPhone) url += `${url.includes('?') ? '&' : '?'}client_phone=${clientPhone}`;
    return this.http.get<any[]>(url);
  }

  getAppointmentById(id: number): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/appointments/api/appointments/${id}/`);
  }

  createAppointment(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/api/appointments/`, data);
  }

  updateAppointment(id: number, data: any): Observable<any> {
    return this.http.patch(`${this.baseUrl}/appointments/api/appointments/${id}/`, data);
  }

  deleteAppointment(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/appointments/api/appointments/${id}/`);
  }

  getRevenueReport(centerId?: number, startDate?: string, endDate?: string): Observable<any> {
    let url = `${this.baseUrl}/staff/api/reports/revenue/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getUsageReport(startDate?: string, endDate?: string, centerId?: number): Observable<any> {
    let url = `${this.baseUrl}/staff/api/reports/usage/`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any>(url);
  }

  getCommissionReport(startDate: string, endDate: string): Observable<any[]> {
    let url = `${this.baseUrl}/staff/api/members/commission_report/?start_date=${startDate}&end_date=${endDate}`;
    return this.http.get<any[]>(url);
  }

  getIncentiveReport(startDate: string, endDate: string, centerId?: number, frequency: string = 'monthly'): Observable<any[]> {
    let url = `${this.baseUrl}/finance/api/reports/incentive-calculation/?start_date=${startDate}&end_date=${endDate}&frequency=${frequency}`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  getIncentiveRules(centerId?: any, category?: string, frequency?: string): Observable<any[]> {
    let url = `${this.baseUrl}/finance/api/rules/`;
    if (centerId !== undefined && centerId !== null) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (category) url += `${url.includes('?') ? '&' : '?'}category=${category}`;
    if (frequency) url += `${url.includes('?') ? '&' : '?'}frequency=${frequency}`;
    return this.http.get<any[]>(url);
  }

  createIncentiveRule(data: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/finance/api/rules/`, data);
  }

  updateIncentiveRule(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/finance/api/rules/${id}/`, data);
  }

  duplicateIncentiveRule(id: number, targetCenterId?: number | null): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/finance/api/rules/${id}/duplicate/`, { target_center_id: targetCenterId });
  }

  deleteIncentiveRule(id: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/finance/api/rules/${id}/`);
  }

  getIncentiveConfigs(centerId?: number): Observable<any[]> {
    let url = `${this.baseUrl}/finance/api/incentives/`;
    if (centerId) url += `?center_id=${centerId}`;
    return this.http.get<any[]>(url);
  }

  createIncentiveConfig(data: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/finance/api/incentives/`, data);
  }

  updateIncentiveConfig(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/finance/api/incentives/${id}/`, data);
  }

  deleteIncentiveConfig(id: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/finance/api/incentives/${id}/`);
  }

  getDashboardStaff(centerId?: number, startDate?: string, endDate?: string): Observable<any> {
    let url = `${this.baseUrl}/salon_admin/api/dashboard/staff/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getDashboardServicesProducts(centerId?: number, startDate?: string, endDate?: string): Observable<any> {
    let url = `${this.baseUrl}/salon_admin/api/dashboard/services_products/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getDashboardData(centerId?: number, startDate?: string, endDate?: string): Observable<any> {
    let url = `${this.baseUrl}/salon_admin/api/dashboard/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getClientServiceHistory(clientId: string | number): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/clients/api/clients/${clientId}/service_history/`);
  }

  carryOverClientPerk(clientId: string | number, payload: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/clients/api/clients/${clientId}/carry-over/`, payload);
  }

  // --- Finance ---
  getRegisterSummary(centerId?: number, startDate?: string, endDate?: string): Observable<any> {
    let url = `${this.baseUrl}/finance/api/register_summary/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getPettyCashEntries(centerId?: number, startDate?: string, endDate?: string): Observable<any[]> {
    let url = `${this.baseUrl}/finance/api/petty-cash/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any[]>(url);
  }

  createPettyCashEntry(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/finance/api/petty-cash/`, data);
  }

  updatePettyCashEntry(id: number, data: any): Observable<any> {
    return this.http.patch(`${this.baseUrl}/finance/api/petty-cash/${id}/`, data);
  }

  getDailyClosings(centerId?: number, date?: string, startDate?: string, endDate?: string): Observable<any[]> {
    let url = `${this.baseUrl}/finance/api/daily-closing/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (date) url += `${url.includes('?') ? '&' : '?'}date=${date}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any[]>(url);
  }

  submitDailyClosing(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/finance/api/daily-closing/`, data);
  }

  getShifts(centerId?: number, status?: string): Observable<any[]> {
    let url = `${this.baseUrl}/finance/api/shifts/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (status) url += `${url.includes('?') ? '&' : '?'}status=${status}`;
    return this.http.get<any[]>(url);
  }

  openShift(centerId: number, startingFloat: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/finance/api/shifts/`, { center: centerId, starting_float: startingFloat });
  }

  closeShift(shiftId: number, actualCash: number, expectedCash: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/finance/api/shifts/${shiftId}/close_shift/`, { actual_cash: actualCash, expected_cash: expectedCash });
  }

  getMonthlySales(centerId?: number, startDate?: string, endDate?: string): Observable<any[]> {
    let url = `${this.baseUrl}/finance/api/monthly_sales/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any[]>(url);
  }

  getDetailedRevenues(centerId?: number, startDate?: string, endDate?: string, page: number = 1, pageSize: number = 100): Observable<any> {
    let url = `${this.baseUrl}/finance/api/detailed_revenues/?page=${page}&page_size=${pageSize}`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getFinanceRefunds(centerId?: number, startDate?: string, endDate?: string): Observable<any> {
    let url = `${this.baseUrl}/finance/api/refunds/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getProcurementReport(centerId?: number, startDate?: string, endDate?: string): Observable<any> {
    let url = `${this.baseUrl}/finance/api/procurement/`;
    if (centerId) url += `${url.includes('?') ? '&' : '?'}center_id=${centerId}`;
    if (startDate) url += `${url.includes('?') ? '&' : '?'}start_date=${startDate}`;
    if (endDate) url += `${url.includes('?') ? '&' : '?'}end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  // --- File Upload ---
  uploadFile(endpoint: string, file: File, centerId?: number | null): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    if (centerId) {
      formData.append('center_id', String(centerId));
    }
    return this.http.post(`${this.baseUrl}/${endpoint}`, formData);
  }

}
