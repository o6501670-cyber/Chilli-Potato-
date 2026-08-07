import { Component, OnInit, inject, OnDestroy, ViewChild, ElementRef, AfterViewChecked, ChangeDetectorRef } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../services/auth';
import { ApiService } from '../services/api';

@Component({
  selector: 'app-admin',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule, FormsModule],
  templateUrl: './admin.html',
  styleUrl: './admin.css',
})
export class AdminComponent implements OnInit, OnDestroy, AfterViewChecked {
  authService = inject(AuthService);
  apiService = inject(ApiService);
  router = inject(Router);
  cdr = inject(ChangeDetectorRef);
  permissions: any = {};
  isOwner = false;
  hasGlobalAccess = false;
  displayName = 'User';
  displayRole = 'Staff';
  displayInitials = 'U';
  displayFirstName = 'User';

  get greeting(): string {
    const h = new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
  }
  @ViewChild('chatScrollContainer') chatScrollContainer!: ElementRef;

  ngOnInit() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        this.permissions = user.permissions || {};
        this.isOwner = (user.role && user.role.toLowerCase() === 'owner') || user.is_superuser === true;
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true) || (user?.role?.permissions?.all_centers === true);
        this.currentUserId = user.user_id;
        this.displayName = user.full_name || user.email || 'User';
        this.displayRole = user.designation || user.role || (user.is_superuser ? 'Super Admin' : 'Staff');
        this.displayFirstName = this.displayName.trim().split(' ')[0];
        const parts = this.displayName.trim().split(' ');
        this.displayInitials = parts.length >= 2
          ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
          : this.displayName.slice(0, 2).toUpperCase();
      } catch (e) {
        console.error('Failed to parse user from localStorage', e);
      }
    }
    
    // Theme logic
    const savedTheme = localStorage.getItem('theme') || 'light';
    this.currentTheme = (savedTheme === 'default' || savedTheme === 'light') ? 'light' : savedTheme;
    this.applyTheme();

    this.startGlobalPolling();
  }

  currentTheme = 'light';

  toggleTheme() {
    if (this.currentTheme === 'light') {
      this.currentTheme = 'dark';
    } else if (this.currentTheme === 'dark') {
      this.currentTheme = 'colorful';
    } else {
      this.currentTheme = 'light';
    }
    this.applyTheme();
    localStorage.setItem('theme', this.currentTheme);
  }

  applyTheme() {
    if (this.currentTheme === 'light' || this.currentTheme === 'default') {
      document.body.removeAttribute('data-theme');
    } else {
      document.body.setAttribute('data-theme', this.currentTheme);
    }
  }

  hasModuleReadAccess(modName: string): boolean {
    const mod = this.permissions[modName];
    if (!mod || typeof mod !== 'object') return false;
    return Object.values(mod).some((sub: any) => sub && sub.read === true);
  }

  logout() {
    this.authService.logout();
  }

  get isAdminPage(): boolean {
    const url = this.router.url;
    return url.includes('/admin/centers') || 
           url.includes('/admin/users') || 
           url.includes('/admin/roles') ||
           url.includes('/admin/services') ||
           url.includes('/admin/clients') ||
           url.includes('/admin/bills') ||
           url.includes('/admin/changes') ||
           url.includes('/admin/manager-discounts');
  }

  get isInventoryPage(): boolean {
    return this.router.url.includes('/admin/inventory');
  }

  get isBillingPage(): boolean {
    return this.router.url.includes('/admin/billing');
  }

  get isMarketingPage(): boolean {
    return this.router.url.includes('/admin/marketing');
  }

  get isStaffPage(): boolean {
    return this.router.url.includes('/admin/staff');
  }

  get isAppointmentsPage(): boolean {
    return this.router.url.includes('/admin/appointments');
  }

  get isDashboardPage(): boolean {
    return this.router.url.includes('/admin/dashboard');
  }

  get isHomePage(): boolean {
    return this.router.url.includes('/admin/home');
  }

  get isFinancePage(): boolean {
    return this.router.url.includes('/admin/finance');
  }

  get isLogsPage(): boolean {
    return this.router.url.includes('/admin/logs');
  }

  get hideAdminHeader(): boolean {
    return this.isInventoryPage || this.isMarketingPage || this.isStaffPage || this.isAppointmentsPage || this.isBillingPage || this.isDashboardPage || this.isHomePage || this.isFinancePage || this.isLogsPage;
  }

  // --- Chat Logic ---
  isChatOpen = false;
  chatUsers: any[] = [];
  chatError: string = '';
  selectedChatUser: any = null;
  chatMessages: any[] = [];
  newMessage: string = '';
  currentUserId: number | null = null;
  selectedImage: File | null = null;
  private chatPollingInterval: any;
  
  unreadChatCount = 0;
  lowStockCount = 0;
  private globalPollingInterval: any;
  consecutiveGlobalErrors = 0;

  startGlobalPolling() {
    this.consecutiveGlobalErrors = 0;
    this.fetchUnreadChatCount();
    this.fetchLowStockCount();
    this.globalPollingInterval = setInterval(() => {
      this.fetchUnreadChatCount();
      this.fetchLowStockCount();
    }, 30000); // check unread every 30 seconds
  }

  stopGlobalPolling() {
    if (this.globalPollingInterval) {
      clearInterval(this.globalPollingInterval);
      this.globalPollingInterval = null;
    }
  }

  fetchUnreadChatCount() {
    this.apiService.getUnreadChatCount().subscribe({
      next: (res: any) => {
        this.consecutiveGlobalErrors = 0;
        this.unreadChatCount = res.count || 0;
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        this.handleGlobalError(err);
      }
    });
  }

  fetchLowStockCount() {
    this.apiService.getLowStockAlerts().subscribe({
      next: (res: any[]) => {
        this.consecutiveGlobalErrors = 0;
        this.lowStockCount = res ? res.length : 0;
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        this.handleGlobalError(err);
      }
    });
  }

  handleGlobalError(err: any) {
    this.consecutiveGlobalErrors++;
    if (this.consecutiveGlobalErrors > 5) {
      console.error('Global polling failed repeatedly. Stopping.', err);
      this.stopGlobalPolling();
    }
  }

  toggleChat() {
    this.isChatOpen = !this.isChatOpen;
    if (this.isChatOpen) {
      this.fetchChatUsers();
    } else {
      this.selectedChatUser = null;
      this.stopChatPolling();
    }
  }

  fetchChatUsers() {
    this.chatError = '';
    this.apiService.get(`accounts/api/chat/users/?t=${new Date().getTime()}`).subscribe({
      next: (users: any) => {
        // Handle potential DRF pagination wrapped object
        this.chatUsers = Array.isArray(users) ? users : (users.data || users.results || []);
        this.cdr.detectChanges(); // Force UI update
      },
      error: (err: any) => {
        console.error('Failed to load chat users', err);
        this.chatError = err.message || 'Unknown error occurred';
        this.cdr.detectChanges();
      }
    });
  }

  selectChatUser(user: any) {
    this.selectedChatUser = user;
    this.newMessageMentions = [];
    this.chatMessages = []; // Clear previous messages immediately
    this.cdr.detectChanges(); // Update UI immediately
    this.fetchChatMessages();
    this.startChatPolling();
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      if (this.chatScrollContainer) {
        this.chatScrollContainer.nativeElement.scrollTop = this.chatScrollContainer.nativeElement.scrollHeight;
      }
    } catch(err) { }
  }

  consecutiveChatErrors = 0;

  fetchChatMessages() {
    if (!this.selectedChatUser) return;
    this.apiService.get(`accounts/api/chat/messages/?user_id=${this.selectedChatUser.id}&t=${new Date().getTime()}`).subscribe({
      next: (msgs: any) => {
        this.consecutiveChatErrors = 0;
        // Handle potential DRF pagination wrapped object
        let parsed = msgs;
        if (typeof msgs === 'string') {
           try { parsed = JSON.parse(msgs); } catch(e) {}
        }
        this.chatMessages = Array.isArray(parsed) ? parsed : (parsed.data || parsed.results || []);
        this.cdr.detectChanges();
        this.scrollToBottom();
      },
      error: (err: any) => {
        this.consecutiveChatErrors++;
        if (this.consecutiveChatErrors > 5) {
          console.error('Failed to load messages repeatedly. Stopping chat polling.', err);
          this.stopChatPolling();
        } else {
          console.warn('Failed to load messages', err);
        }
      }
    });
  }

  startChatPolling() {
    this.stopChatPolling();
    this.consecutiveChatErrors = 0;
    this.chatPollingInterval = setInterval(() => {
      this.fetchChatMessages();
    }, 10000); // poll messages every 10 seconds
  }

  stopChatPolling() {
    if (this.chatPollingInterval) {
      clearInterval(this.chatPollingInterval);
      this.chatPollingInterval = null;
    }
  }

  onChatFileSelected(event: any) {
    if (event.target.files && event.target.files.length > 0) {
      this.selectedImage = event.target.files[0];
    }
  }

  mentionSearch = '';
  showMentionDropdown = false;
  allStaffUsers: any[] = [];
  filteredMentionUsers: any[] = [];
  mentionStartIndex = -1;

  fetchStaffUsers() {
    this.apiService.get('accounts/api/users/').subscribe({
      next: (res: any) => {
        this.allStaffUsers = Array.isArray(res) ? res : (res.results || res.data || []);
      },
      error: (err) => console.error('Failed to load staff users', err)
    });
  }

  onChatInput(event: any) {
    const text = event.target.value || '';
    const cursor = event.target.selectionStart || 0;
    
    // Check if we are typing a mention
    const textBeforeCursor = text.substring(0, cursor);
    const match = textBeforeCursor.match(/@(\w*)$/);
    
    if (match) {
      this.showMentionDropdown = true;
      this.mentionSearch = match[1].toLowerCase();
      this.mentionStartIndex = cursor - match[1].length - 1;
      
      if (!this.allStaffUsers.length) {
         this.fetchStaffUsers();
      }
      
      this.filteredMentionUsers = this.allStaffUsers.filter(u => 
        (u.full_name || '').toLowerCase().includes(this.mentionSearch) ||
        (u.email || '').toLowerCase().includes(this.mentionSearch)
      ).slice(0, 5); // show max 5
    } else {
      this.showMentionDropdown = false;
    }
  }

  selectMention(user: any) {
    const text = this.newMessage || '';
    const before = text.substring(0, this.mentionStartIndex);
    const after = text.substring(this.mentionSearch.length + this.mentionStartIndex + 1);
    // Use a special tag or just the name
    this.newMessage = before + '@' + user.full_name + ' ' + after;
    this.showMentionDropdown = false;
    
    // We also need to send the mentioned user ID to the backend!
    if (!this.newMessageMentions) this.newMessageMentions = [];
    if (!this.newMessageMentions.includes(user.id)) {
        this.newMessageMentions.push(user.id);
    }
  }

  newMessageMentions: number[] = [];

  sendMessage() {
    if (!this.newMessage.trim() && !this.selectedImage) return;
    if (!this.selectedChatUser) return;

    const formData = new FormData();
    // selectedChatUser is now a Room! We send room_id
    formData.append('room_id', this.selectedChatUser.id);
    if (this.newMessage.trim()) {
      formData.append('content', this.newMessage.trim());
    }
    if (this.selectedImage) {
      formData.append('image', this.selectedImage);
    }
    if (this.newMessageMentions && this.newMessageMentions.length > 0) {
      formData.append('mentions', JSON.stringify(this.newMessageMentions));
    }

    this.apiService.post('accounts/api/chat/messages/', formData).subscribe({
      next: (res: any) => {
        this.newMessage = '';
        this.selectedImage = null;
        this.newMessageMentions = [];
        this.fetchChatMessages();
      },
      error: (err: any) => console.error('Failed to send message', err)
    });
  }

  ngOnDestroy() {
    this.stopChatPolling();
    this.stopGlobalPolling();
  }
}
