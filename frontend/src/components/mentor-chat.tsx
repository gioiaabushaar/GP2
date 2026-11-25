"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Input } from "./ui";

type Message = { from: "mentor" | "me"; text: string; meta?: string; error?: boolean };

export function MentorChat({ challengeId, onHint }: { challengeId: number; onHint: () => void }) {
  const [messages, setMessages] = useState<Message[]>([
    { from: "mentor", text: "Hello! I'm your AI Mentor. How can I assist you with this challenge?" },
  ]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (q.length < 3) return;
    setMessages((m) => [...m, { from: "me", text: q }]);
    setQuestion("");
    setBusy(true);
    try {
      const res = await api.hint(challengeId, q);
      setMessages((m) => [...m, { from: "mentor", text: res.hint, meta: `Hint level ${res.hint_level} of 3 · Source: ${res.source}` }]);
      onHint();
    } catch (err) {
      setMessages((m) => [...m, { from: "mentor", text: err instanceof Error ? err.message : "The mentor is unavailable.", error: true }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="RAG AI Mentor" className="flex flex-col">
      <p className="-mt-2 mb-3 text-xs italic text-muted">Hints come from the team&apos;s write-ups and never reveal the flag.</p>
      <div className="flex h-72 flex-col gap-2 overflow-y-auto rounded-lg bg-bg/60 p-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
              m.from === "me"
                ? "self-end bg-white/10 text-white"
                : m.error
                  ? "self-start border-l-2 border-bad bg-bad/10 text-bad"
                  : "self-start border-l-2 border-accent bg-accent/10 text-white"
            }`}
          >
            <p className="whitespace-pre-wrap">{m.text}</p>
            {m.meta && <p className="mt-1 text-[11px] text-muted">{m.meta}</p>}
          </div>
        ))}
        {busy && <p className="self-start text-xs text-muted">Mentor is thinking…</p>}
        <div ref={bottom} />
      </div>
      <form onSubmit={send} className="mt-3 flex gap-2">
        <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask for a hint…" maxLength={500} aria-label="Question for the mentor" />
        <Button type="submit" variant="secondary" busy={busy} disabled={question.trim().length < 3}>
          Send
        </Button>
      </form>
    </Card>
  );
}
