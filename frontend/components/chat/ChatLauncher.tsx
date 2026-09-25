'use client';

import { useState } from 'react';
import { MessageCircleMore } from 'lucide-react';
import { ChatPanel } from './ChatPanel';

/** The nav button that opens the chat panel. The conversation lives as long as the page. */
export function ChatLauncher() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label="Chat - ask about this page"
        className="flex items-center gap-1.5 rounded-full bg-gold p-2 sm:py-1.5 sm:pr-3 sm:pl-2 text-sm font-semibold text-gold-foreground shadow-[0_0_16px_rgb(233_196_106/0.35)] transition hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold"
      >
        <MessageCircleMore className="h-4 w-4" aria-hidden />
        <span aria-hidden className="hidden sm:inline">Chat</span>
      </button>
      <ChatPanel open={open} onClose={() => setOpen(false)} />
    </>
  );
}
