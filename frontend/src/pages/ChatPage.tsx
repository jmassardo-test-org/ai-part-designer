/**
 * Chat-based Part Design Page.
 * 
 * Provides a conversational interface for designing CAD parts.
 */

import { ChatPanel } from '@/components/chat';

export function ChatPage() {
  return (
    <div className="h-[calc(100vh-64px)]">
      <ChatPanel className="h-full" />
    </div>
  );
}
