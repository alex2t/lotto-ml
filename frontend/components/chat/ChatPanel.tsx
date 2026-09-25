'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import { Send, X } from 'lucide-react';
import type { ChatReply, Source } from '@/lib/chat/answer';
import { currentLine, currentMethod } from '@/lib/pick/current-line';

/**
 * The chat panel (chat.md 7): a right-hand sheet on a wide screen, a bottom sheet on a phone.
 *
 * A native modal <dialog>, so focus is trapped and Escape closes it. It opens with the
 * suggested questions for the page, which are answered for free. Nothing here decides what
 * an answer says - the whole answer arrives from /api/chat already checked (chat.md 6).
 */

interface Exchange {
  question: string;
  reply?: Pick<ChatReply, 'answer' | 'source'>;
}

const SOURCE_LABEL: Record<Source, string> = {
  prepared: 'Prepared answer',
  data: 'From the data',
  cache: 'Written earlier from this page\'s figures',
  model: 'Written from this page\'s figures',
  guarded: 'Held back',
  unavailable: '',
};

const MAX_QUESTION = 500;

export function ChatPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const d = dialog.current!;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  // The dialog is modal, so the picking method cannot change while it is open: reading it on
  // opening is enough to offer the questions for what is on screen.
  useEffect(() => {
    if (!open) return;
    const query = new URLSearchParams({ pathname });
    const method = currentMethod();
    if (pathname === '/pick' && method) query.set('method', method);
    if (pathname === '/pick' && currentLine().length === 6) query.set('line', 'complete');
    fetch(`/api/chat?${query}`)
      .then((r) => r.json())
      .then((body: { suggestions: string[] }) => setSuggestions(body.suggestions));
  }, [open, pathname]);

  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' });
  }, [exchanges, busy]);

  async function ask(text: string) {
    const question = text.trim();
    if (!question || busy) return;
    const history = exchanges
      .filter((e) => e.reply)
      .slice(-2)
      .map((e) => ({ question: e.question, answer: e.reply!.answer }));
    const line = currentLine();

    setExchanges((c) => [...c, { question }]);
    setDraft('');
    setBusy(true);
    let reply: Exchange['reply'];
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          pathname,
          search: window.location.search,
          line: pathname === '/pick' && line.length === 6 ? line : undefined,
          method: pathname === '/pick' ? currentMethod() : undefined,
          history,
        }),
      });
      const body = await res.json();
      reply = res.ok ? body : { answer: body.error, source: 'unavailable' };
    } catch {
      reply = { answer: 'The panel could not reach the site. Try again in a moment.', source: 'unavailable' };
    }
    setExchanges((c) => c.map((e, i) => (i === c.length - 1 ? { ...e, reply } : e)));
    setBusy(false);
  }

  return (
    <dialog
      ref={dialog}
      aria-labelledby="chat-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialog.current) onClose();
      }}
      className="chat-sheet fixed inset-x-0 top-auto bottom-0 m-0 h-[85dvh] max-h-none w-full max-w-none flex-col rounded-t-2xl border-t border-border bg-background p-0 text-foreground open:flex sm:inset-y-0 sm:right-0 sm:left-auto sm:h-full sm:w-[26rem] sm:rounded-none sm:border-t-0 sm:border-l"
    >
      <header className="flex items-start gap-3 border-b border-border px-4 py-3">
        <div className="mr-auto">
          <h2 id="chat-title" className="text-sm font-semibold">
            Ask about this page
          </h2>
          <p className="text-xs text-muted">
            Answers describe past draws. Every line is equally likely to win.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close the questions panel"
          className="rounded-full border border-border p-2 text-muted hover:text-foreground"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <ol aria-live="polite" className="flex flex-col gap-3 text-sm">
          {exchanges.map((e, i) => (
            <li key={i} className="flex flex-col gap-1">
              <p className="self-end rounded-2xl bg-surface px-3 py-2">{e.question}</p>
              {e.reply && (
                <div className="flex flex-col gap-0.5">
                  <p className="whitespace-pre-line">{e.reply.answer}</p>
                  {SOURCE_LABEL[e.reply.source] && (
                    <p className="text-xs text-muted">{SOURCE_LABEL[e.reply.source]}</p>
                  )}
                </div>
              )}
            </li>
          ))}
        </ol>
        {busy && <p className="mt-3 text-sm text-muted">Looking that up...</p>}

        <section aria-labelledby="chat-suggested" className="mt-4 flex flex-col gap-2">
          <h3 id="chat-suggested" className="text-xs uppercase tracking-widest text-muted">
            Suggested
          </h3>
          <ul className="flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <li key={s}>
                <button
                  type="button"
                  onClick={() => ask(s)}
                  disabled={busy}
                  className="rounded-full border border-border px-3 py-1.5 text-left text-xs hover:bg-surface disabled:opacity-60"
                >
                  {s}
                </button>
              </li>
            ))}
          </ul>
        </section>
        <div ref={end} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(draft);
        }}
        className="flex items-center gap-2 border-t border-border px-4 py-3"
      >
        <label htmlFor="chat-question" className="sr-only">
          Your question
        </label>
        <input
          id="chat-question"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          maxLength={MAX_QUESTION}
          placeholder="Ask about a number, a table or a word"
          autoComplete="off"
          className="min-w-0 flex-1 rounded-full border border-border bg-surface px-4 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={busy || !draft.trim()}
          aria-label="Ask"
          className="rounded-full bg-accent p-2 text-accent-foreground disabled:opacity-60"
        >
          <Send className="h-4 w-4" aria-hidden />
        </button>
      </form>
    </dialog>
  );
}
