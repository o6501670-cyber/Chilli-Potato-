import { Injectable } from '@angular/core';
import { Subject, Observable, BehaviorSubject } from 'rxjs';

export interface ChatMessage {
  id: number;
  sender_id: number;
  sender_name: string;
  content: string;
  timestamp: string;
  status: 'sent' | 'delivered' | 'read';
  image?: string;
  is_deleted?: boolean;
  reply_to?: {
    id: number;
    sender_name: string;
    content: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ChatWebsocketService {
  private socket: WebSocket | null = null;
  private currentRoomId: number | null = null;
  
  // Observables for various events
  private messageSubject = new Subject<ChatMessage>();
  private typingSubject = new Subject<{user_id: number, user_name: string, is_typing: boolean}>();
  private readReceiptSubject = new Subject<{message_ids: number[], reader_id: number}>();
  private onlineSubject = new Subject<{user_id: number, is_online: boolean}>();
  private reactionSubject = new Subject<{message_id: number, emoji: string, action: string, user_id: number}>();
  private deleteSubject = new Subject<{message_id: number, deleted_by: number}>();
  private editSubject = new Subject<{message_id: number, content: string, edited_by: number}>();
  
  public isConnected$ = new BehaviorSubject<boolean>(false);

  messages$ = this.messageSubject.asObservable();
  typing$ = this.typingSubject.asObservable();
  readReceipts$ = this.readReceiptSubject.asObservable();
  onlineStatus$ = this.onlineSubject.asObservable();
  reactions$ = this.reactionSubject.asObservable();
  deletes$ = this.deleteSubject.asObservable();
  edits$ = this.editSubject.asObservable();

  connect(roomId: number) {
    if (this.socket && this.currentRoomId === roomId) {
      return; // Already connected to this room
    }
    
    this.disconnect();
    this.currentRoomId = roomId;
    
    const token = localStorage.getItem('token');
    if (!token) return;

    // Use ws:// for http, wss:// for https
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // For local dev where backend is typically 8000
    const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
    
    this.socket = new WebSocket(`${protocol}//${host}/ws/chat/${roomId}/?token=${token}`);

    this.socket.onopen = () => {
      this.isConnected$.next(true);
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleIncomingMessage(data);
      } catch (e) {
        console.error('Failed to parse websocket message', e);
      }
    };

    this.socket.onclose = () => {
      this.isConnected$.next(false);
      // Optional: implement exponential backoff reconnection here
    };
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.currentRoomId = null;
      this.isConnected$.next(false);
    }
  }

  private handleIncomingMessage(data: any) {
    switch (data.type) {
      case 'chat_message':
        this.messageSubject.next(data as ChatMessage);
        break;
      case 'typing':
        this.typingSubject.next(data);
        break;
      case 'messages_read':
        this.readReceiptSubject.next(data);
        break;
      case 'user_online':
        this.onlineSubject.next({user_id: data.user_id, is_online: true});
        break;
      case 'user_offline':
        this.onlineSubject.next({user_id: data.user_id, is_online: false});
        break;
      case 'reaction_update':
        this.reactionSubject.next(data);
        break;
      case 'message_deleted':
        this.deleteSubject.next(data);
        break;
      case 'message_edited':
        this.editSubject.next(data);
        break;
    }
  }

  sendMessage(content: string, replyToId?: number) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: 'chat_message',
        content: content,
        reply_to_id: replyToId
      }));
    }
  }

  sendTypingStatus(isTyping: boolean) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: isTyping ? 'typing' : 'stop_typing'
      }));
    }
  }

  sendReadReceipt(messageIds: number[]) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN && messageIds.length > 0) {
      this.socket.send(JSON.stringify({
        type: 'read_receipt',
        message_ids: messageIds
      }));
    }
  }

  sendReaction(messageId: number, emoji: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: 'reaction',
        message_id: messageId,
        emoji: emoji
      }));
    }
  }

  deleteMessage(messageId: number) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: 'delete_message',
        message_id: messageId
      }));
    }
  }

  editMessage(messageId: number, content: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: 'edit_message',
        message_id: messageId,
        content: content
      }));
    }
  }
}
