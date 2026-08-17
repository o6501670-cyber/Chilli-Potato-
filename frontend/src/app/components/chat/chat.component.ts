import { Component, OnInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { Subscription } from 'rxjs';
import { ChatWebsocketService, ChatMessage } from './chat-websocket.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent implements OnInit, OnDestroy {
  @ViewChild('chatScrollContainer') chatScrollContainer!: ElementRef;
  @ViewChild('chatFileInput') chatFileInput!: ElementRef;

  isOpen = false;
  rooms: any[] = [];
  selectedRoom: any = null;
  messages: ChatMessage[] = [];
  
  newMessage = '';
  selectedImage: File | null = null;
  imagePreview: string | null = null;
  
  currentUserId: number | null = null;
  
  // Real-time state
  typingUsers = new Set<string>();
  onlineUsers = new Set<number>();
  
  // Pagination
  nextUrl: string | null = null;
  isLoadingMore = false;
  
  // Context menu & features
  replyingTo: ChatMessage | null = null;
  showEmojiPickerFor: number | null = null;
  contextMenuMsg: number | null = null;

  get typingUsersArray(): string[] {
    return Array.from(this.typingUsers);
  }

  getAvatarUrl(seed: any): string {
    // Uses DiceBear Micah style for an aesthetic, trendy, cool vibe
    return `https://api.dicebear.com/9.x/micah/svg?seed=${encodeURIComponent(String(seed || 'User'))}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf`;
  }

  // Subscriptions
  private subs = new Subscription();
  private typingTimeout: any;

  constructor(
    private api: ApiService,
    private ws: ChatWebsocketService,
    private cdr: ChangeDetectorRef,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit() {
    if (isPlatformBrowser(this.platformId)) {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        try {
          const user = JSON.parse(userStr);
          this.currentUserId = user.id;
        } catch (e) {}
      }
      this.fetchRooms();
      this.setupWebsocketListeners();
    }
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.ws.disconnect();
  }

  toggleChat() {
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.fetchRooms();
    } else {
      this.selectedRoom = null;
      this.ws.disconnect();
    }
    this.cdr.detectChanges();
  }

  // --- ROOMS LIST ---
  fetchRooms() {
    this.api.get('accounts/api/chat/users/').subscribe({
      next: (res) => {
        // Handle DRF pagination just in case
        this.rooms = Array.isArray(res) ? res : (res.results || res.data || []);
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Failed to load rooms', err)
    });
  }

  selectRoom(room: any) {
    this.selectedRoom = room;
    this.messages = [];
    this.nextUrl = null;
    this.replyingTo = null;
    this.typingUsers.clear();
    
    // Fetch initial messages via REST with cursor
    this.fetchMessages();
    
    // Connect WebSocket
    this.ws.connect(room.id);
  }

  // --- MESSAGES ---
  fetchMessages(loadMore = false) {
    if (!this.selectedRoom) return;
    
    const url = loadMore && this.nextUrl 
      ? this.nextUrl.replace(window.location.origin, '') 
      : `accounts/api/chat/messages/?room_id=${this.selectedRoom.id}`;
      
    if (loadMore) this.isLoadingMore = true;

    this.api.get(url).subscribe({
      next: (res) => {
        // DRF Cursor Pagination returns {next, previous, results}
        const results = res.results || res;
        this.nextUrl = res.next || null;
        
        // Reverse because cursor pagination with ordering='-timestamp' gives newest first
        const newMsgs = Array.isArray(results) ? [...results].reverse() : [];
        
        if (loadMore) {
          // Prepend older messages
          const oldHeight = this.chatScrollContainer.nativeElement.scrollHeight;
          this.messages = [...newMsgs, ...this.messages];
          this.cdr.detectChanges();
          // Maintain scroll position
          setTimeout(() => {
            const newHeight = this.chatScrollContainer.nativeElement.scrollHeight;
            this.chatScrollContainer.nativeElement.scrollTop = newHeight - oldHeight;
          }, 0);
        } else {
          this.messages = newMsgs;
          this.scrollToBottom();
          this.markRoomAsRead();
        }
        this.isLoadingMore = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Failed to fetch messages', err);
        this.isLoadingMore = false;
      }
    });
  }

  onScroll(event: any) {
    if (event.target.scrollTop === 0 && this.nextUrl && !this.isLoadingMore) {
      this.fetchMessages(true);
    }
  }

  scrollToBottom() {
    setTimeout(() => {
      if (this.chatScrollContainer) {
        this.chatScrollContainer.nativeElement.scrollTop = this.chatScrollContainer.nativeElement.scrollHeight;
      }
    }, 100);
  }

  // --- WEBSOCKET LISTENERS ---
  private setupWebsocketListeners() {
    this.subs.add(
      this.ws.messages$.subscribe(msg => {
        this.messages.push(msg);
        this.scrollToBottom();
        this.cdr.detectChanges();
        
        // If message is from someone else, mark as read
        if (msg.sender_id !== this.currentUserId) {
          this.ws.sendReadReceipt([msg.id]);
        }
      })
    );

    this.subs.add(
      this.ws.typing$.subscribe(data => {
        if (data.is_typing) {
          this.typingUsers.add(data.user_name);
        } else {
          this.typingUsers.delete(data.user_name);
        }
        this.cdr.detectChanges();
      })
    );

    this.subs.add(
      this.ws.readReceipts$.subscribe(data => {
        // Update status of our messages that were read
        this.messages.forEach(m => {
          if (data.message_ids.includes(m.id)) {
            m.status = 'read';
          }
        });
        this.cdr.detectChanges();
      })
    );

    this.subs.add(
      this.ws.onlineStatus$.subscribe(data => {
        if (data.is_online) this.onlineUsers.add(data.user_id);
        else this.onlineUsers.delete(data.user_id);
        this.cdr.detectChanges();
      })
    );
    
    this.subs.add(
      this.ws.reactions$.subscribe(data => {
         const msg = this.messages.find(m => m.id === data.message_id);
         if (msg) {
             // To properly handle reactions in UI, we need to update the summary
             // For simplicity, we just trigger a refetch of that message or append manually
             // Here we'll do a simple REST refetch of the single message if possible, or ignore for MVP
         }
      })
    );
    
    this.subs.add(
      this.ws.deletes$.subscribe(data => {
         const msg = this.messages.find(m => m.id === data.message_id);
         if (msg) {
             msg.content = '';
             msg.is_deleted = true;
             this.cdr.detectChanges();
         }
      })
    );
  }

  // --- SENDING ---
  onTyping(event: any) {
    this.ws.sendTypingStatus(true);
    clearTimeout(this.typingTimeout);
    this.typingTimeout = setTimeout(() => {
      this.ws.sendTypingStatus(false);
    }, 2000);
  }

  sendMessage() {
    if (!this.newMessage.trim() && !this.selectedImage) return;

    if (this.selectedImage) {
      // Send via REST if there's an image
      const fd = new FormData();
      fd.append('room_id', this.selectedRoom.id);
      if (this.newMessage.trim()) fd.append('content', this.newMessage.trim());
      if (this.replyingTo) fd.append('reply_to', this.replyingTo.id.toString());
      fd.append('image', this.selectedImage);
      
      this.api.post('accounts/api/chat/messages/', fd).subscribe({
        next: () => {
          this.resetInput();
        }
      });
    } else {
      // Send via WS
      this.ws.sendMessage(this.newMessage.trim(), this.replyingTo?.id);
      this.resetInput();
    }
  }

  resetInput() {
    this.newMessage = '';
    this.selectedImage = null;
    this.imagePreview = null;
    this.replyingTo = null;
    this.ws.sendTypingStatus(false);
  }

  onFileSelected(event: any) {
    if (event.target.files && event.target.files.length > 0) {
      this.selectedImage = event.target.files[0];
      // Generate preview
      const reader = new FileReader();
      reader.onload = (e: any) => this.imagePreview = e.target.result;
      reader.readAsDataURL(this.selectedImage!);
    }
  }

  markRoomAsRead() {
    if (!this.selectedRoom) return;
    this.api.post('accounts/api/chat/messages/mark_read/', { room_id: this.selectedRoom.id }).subscribe();
  }

  // --- ACTIONS ---
  toggleContextMenu(msgId: number, event: Event) {
    event.preventDefault();
    if (this.contextMenuMsg === msgId) {
      this.contextMenuMsg = null;
    } else {
      this.contextMenuMsg = msgId;
    }
  }

  replyToMessage(msg: ChatMessage) {
    this.replyingTo = msg;
    this.contextMenuMsg = null;
  }

  deleteMessage(msgId: number) {
    this.ws.deleteMessage(msgId);
    this.contextMenuMsg = null;
  }
}
