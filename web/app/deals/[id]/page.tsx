"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiError, downloadFile } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Agreement, Deal, Message, Offer } from "@/lib/types";
import { formatPKR, humanStatus } from "@/lib/format";
import { OfferBuilder } from "@/components/OfferBuilder";

const NEGOTIABLE = ["CHAT_OPEN", "OFFER_SENT", "COUNTERED"];

export default function DealPage() {
  const { id } = useParams<{ id: string }>();
  const dealId = Number(id);
  const { user } = useAuth();
  const [deal, setDeal] = useState<Deal | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [agreement, setAgreement] = useState<Agreement | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    try {
      const d = await api<Deal>(`/deals/${dealId}`);
      setDeal(d);
      setMessages(await api<Message[]>(`/deals/${dealId}/messages`).catch(() => []));
      setOffers(await api<Offer[]>(`/deals/${dealId}/offers`).catch(() => []));
      setAgreement(await api<Agreement>(`/deals/${dealId}/agreement`).catch(() => null));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load deal.");
    }
  }, [dealId]);

  useEffect(() => {
    if (user) void reload();
  }, [user, reload]);

  if (!user) return <div className="card p-8 text-center text-ink/60"><a href="/verify" className="text-moss underline">Verify</a> to view this deal.</div>;
  if (error) return <div className="card p-8 text-center text-ink/60">{error}</div>;
  if (!deal) return <p className="text-ink/50">Loading…</p>;

  const isTenant = user.id === deal.tenant_id;
  const pendingOffer = offers.find((o) => o.status === "PENDING");
  const canAccept = pendingOffer && pendingOffer.sender_id !== user.id && ["OFFER_SENT", "COUNTERED"].includes(deal.status);

  async function act(path: string, body?: unknown) {
    setError("");
    try {
      await api(path, { method: "POST", body });
      await reload();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Action failed.");
    }
  }

  async function sendChat() {
    if (!chatInput.trim()) return;
    await act(`/deals/${dealId}/messages`, { body: chatInput.trim() });
    setChatInput("");
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-3xl text-moss">Deal #{deal.id}</h1>
        <span className="chip bg-moss/10 text-moss">{humanStatus(deal.status)}</span>
      </div>

      {/* Open chat gate */}
      {deal.status === "INQUIRY" && isTenant && (
        <div className="card p-5">
          {user.cnic_captured ? (
            <button className="btn-primary" onClick={() => void act(`/deals/${dealId}/open`)}>
              Open chat with owner
            </button>
          ) : (
            <p className="text-sm text-ink/70">
              Add your CNIC to open the chat. <a href="/verify" className="text-moss underline">Verify CNIC →</a>
            </p>
          )}
          <p className="mt-2 text-xs text-ink/50">Chat opens only after you verify (anti–call-spam gate).</p>
        </div>
      )}
      {deal.status === "INQUIRY" && !isTenant && (
        <div className="card p-5 text-sm text-ink/70">Waiting for the tenant to verify and open chat.</div>
      )}

      {/* Chat */}
      {deal.status !== "INQUIRY" && (
        <div className="card p-5">
          <p className="font-display text-lg text-moss mb-3">Chat</p>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {messages.map((m) => {
              if (m.type === "system")
                return <p key={m.id} className="text-center text-xs text-ink/50 italic">{m.body}</p>;
              const mine = m.sender_id === user.id;
              return (
                <div key={m.id} className={mine ? "text-right" : ""}>
                  <span className={`inline-block rounded-2xl px-3 py-2 text-sm ${mine ? "bg-moss text-paper" : "bg-paper-dark text-ink"}`}>
                    {m.type === "offer" ? "💰 " : ""}{m.body}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex gap-2">
            <input className="input" value={chatInput} placeholder="Message…"
              onChange={(e) => setChatInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendChat()} />
            <button className="btn-primary" onClick={() => void sendChat()}>Send</button>
          </div>
        </div>
      )}

      {/* Contact privacy gate */}
      {deal.status !== "INQUIRY" && (
        <div className="card p-5">
          <p className="font-display text-lg text-moss">Contact details</p>
          {deal.contact_shared && deal.contact ? (
            <p className="mt-2 text-sm">
              {deal.contact.name ?? "Counter-party"} · <strong>{deal.contact.phone}</strong>
            </p>
          ) : (
            <>
              <p className="mt-1 text-sm text-ink/70">
                Hidden until both sides agree to share. You: {(isTenant ? deal.tenant_consent_contact : deal.owner_consent_contact) ? "agreed ✓" : "not yet"}.
              </p>
              <button className="btn-ghost mt-3" onClick={() => void act(`/deals/${dealId}/share-contact`)}>
                Agree to share my contact
              </button>
            </>
          )}
        </div>
      )}

      {/* Offers */}
      {NEGOTIABLE.includes(deal.status) && <OfferBuilder dealId={dealId} onSent={() => void reload()} />}

      {pendingOffer && (
        <div className="card p-5">
          <p className="font-display text-lg text-moss">Offer on the table</p>
          <p className="mt-1 text-sm">
            {formatPKR(pendingOffer.rent)}/mo · {pendingOffer.advance_months} mo advance · security {formatPKR(pendingOffer.security)} ·
            {" "}{pendingOffer.duration_months} months · move-in {pendingOffer.move_in}
          </p>
          {canAccept && (
            <button className="btn-clay mt-3" onClick={() => void act(`/deals/${dealId}/offers/${pendingOffer.id}/accept`)}>
              Accept this offer
            </button>
          )}
          {pendingOffer.sender_id === user.id && <p className="mt-2 text-xs text-ink/50">Waiting for the other party to respond.</p>}
        </div>
      )}

      {/* Agreement */}
      {["ACCEPTED", "AGREEMENT_GENERATED", "SIGNED_OFFLINE"].includes(deal.status) && (
        <div className="card p-5 space-y-3">
          <p className="font-display text-lg text-moss">Agreement</p>
          {deal.locked_terms && (
            <p className="text-sm text-ink/70">
              Locked terms: {formatPKR(Number(deal.locked_terms.rent))}/mo · {String(deal.locked_terms.advance_months)} mo advance ·
              {" "}{String(deal.locked_terms.duration_months)} months
            </p>
          )}
          {!agreement ? (
            <button className="btn-primary" onClick={() => void act(`/deals/${dealId}/agreement`)}>
              Generate stamp-paper agreement
            </button>
          ) : (
            <>
              <div className="rounded-xl bg-paper-dark/50 p-4 text-sm">
                <p>Stamp duty band: <strong>{agreement.stamp_duty_label}</strong> (annual rent {formatPKR(agreement.annual_rent)})</p>
                <ul className="mt-2 list-disc pl-5 text-ink/70 space-y-1">
                  {agreement.advisories.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              </div>
              <div className="flex flex-wrap gap-2">
                <button className="btn-ghost" onClick={() => void downloadFile(`/deals/${dealId}/agreement/pdf`, `agreement-${dealId}.pdf`)}>
                  Download agreement PDF
                </button>
                <button className="btn-ghost" onClick={() => void downloadFile(`/deals/${dealId}/police-verification-form`, `police-form-${dealId}.pdf`)}>
                  Police verification form
                </button>
                {deal.status === "AGREEMENT_GENERATED" && (
                  <button className="btn-clay" onClick={() => void act(`/deals/${dealId}/sign`)}>Mark signed offline</button>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {error && <p className="text-sm text-clay-dark">{error}</p>}
    </div>
  );
}
