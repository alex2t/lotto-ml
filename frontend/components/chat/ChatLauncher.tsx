'use client';

import { useState } from 'react';
import { MessageCircleQuestion } from 'lucide-react';
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
        aria-label="Ask about this page"
        className="rounded-full border border-border p-2 text-muted hover:text-foreground"
      >
        <MessageCircleQuestion className="h-4 w-4" aria-hidden />
      </button>
      <ChatPanel open={open} onClose={() => setOpen(false)} />
    </>
  );
}
