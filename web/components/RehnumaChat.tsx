"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AskResponse } from "@/lib/types";

type Turn = { role: "user" | "assistant"; content: string };

export function RehnumaChat({ listingId }: { listingId?: number }) {
  const { user } = useAuth();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  async function send() {
    const message = input.trim();
    if (!message || busy) return;
    setTurns((t) => [...t, { role: "user", content: message }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api<AskResponse>("/ai/ask", {
        method: "POST",
        body: { message, listing_id: listingId ?? null, session_id: sessionId },
      });
      setSessionId(res.session_id);
      setTurns((t) => [...t, { role: "assistant", content: res.reply }]);
    } catch {
      setTurns((t) => [...t, { role: "assistant", content: "Rehnuma is unavailable right now. Please try again." }]);
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <div className="card p-5 text-sm text-ink/70">
        <p className="font-medium text-ink">Ask Rehnuma</p>
        <p className="mt-1">
          <a href="/verify" className="text-moss underline">Verify your phone</a> to chat with Rehnuma about this property.
        </p>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <p className="font-display text-lg text-moss">Ask Rehnuma</p>
      <p className="text-xs text-ink/50">Neutral advice — works for the deal, not a commission. English or Roman Urdu.</p>
      <div className="mt-3 space-y-2 max-h-72 overflow-y-auto">
        {turns.length === 0 && (
          <p className="text-sm text-ink/50">e.g. “Is this rent fair?” or “Kiraya kitna theek hai?”</p>
        )}
        {turns.map((t, i) => (
          <div key={i} className={t.role === "user" ? "text-right" : ""}>
            <span
              className={`inline-block rounded-2xl px-3 py-2 text-sm ${
                t.role === "user" ? "bg-moss text-paper" : "bg-paper-dark text-ink"
              }`}
            >
              {t.content}
            </span>
          </div>
        ))}
        {busy && <p className="text-sm text-ink/40">Rehnuma is thinking…</p>}
      </div>
      <div className="mt-3 flex gap-2">
        <input
          className="input"
          value={input}
          placeholder="Ask about rent, advance, the area…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="btn-primary" onClick={() => void send()} disabled={busy}>Send</button>
      </div>
    </div>
  );
}
