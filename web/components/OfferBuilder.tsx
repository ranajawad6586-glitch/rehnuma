"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Fairness, Offer } from "@/lib/types";

export function OfferBuilder({ dealId, onSent }: { dealId: number; onSent: () => void }) {
  const [rent, setRent] = useState("");
  const [advance, setAdvance] = useState("3");
  const [security, setSecurity] = useState("");
  const [duration, setDuration] = useState("12");
  const [moveIn, setMoveIn] = useState("");
  const [fairness, setFairness] = useState<Fairness | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function payload() {
    return {
      rent: Number(rent),
      advance_months: Number(advance),
      security: Number(security || rent),
      duration_months: Number(duration),
      move_in: moveIn,
    };
  }

  async function checkFair() {
    setError("");
    if (!rent) return setError("Enter a rent first.");
    try {
      setFairness(await api<Fairness>(`/deals/${dealId}/offers/check`, { method: "POST", body: payload() }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not check fairness.");
    }
  }

  async function sendOffer() {
    setError("");
    if (!rent || !moveIn) return setError("Rent and move-in date are required.");
    setBusy(true);
    try {
      await api<Offer>(`/deals/${dealId}/offers`, { method: "POST", body: payload() });
      setFairness(null);
      onSent();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not send offer.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-5 space-y-3">
      <p className="font-display text-lg text-moss">Make an offer</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Rent / month</label>
          <input className="input" type="number" value={rent} onChange={(e) => setRent(e.target.value)} />
        </div>
        <div>
          <label className="label">Advance (months)</label>
          <input className="input" type="number" value={advance} onChange={(e) => setAdvance(e.target.value)} />
        </div>
        <div>
          <label className="label">Security (PKR)</label>
          <input className="input" type="number" value={security} placeholder="defaults to 1 month"
            onChange={(e) => setSecurity(e.target.value)} />
        </div>
        <div>
          <label className="label">Term (months)</label>
          <input className="input" type="number" value={duration} onChange={(e) => setDuration(e.target.value)} />
        </div>
        <div className="col-span-2">
          <label className="label">Move-in date</label>
          <input className="input" type="date" value={moveIn} onChange={(e) => setMoveIn(e.target.value)} />
        </div>
      </div>

      {fairness && (
        <div className={`rounded-xl px-4 py-3 text-sm ${fairness.is_fair ? "bg-moss/10 text-moss-dark" : "bg-clay/10 text-clay-dark"}`}>
          <strong>Rehnuma:</strong> {fairness.verdict}
        </div>
      )}
      {error && <p className="text-sm text-clay-dark">{error}</p>}

      <div className="flex gap-2">
        <button className="btn-ghost" onClick={() => void checkFair()}>Is this fair?</button>
        <button className="btn-clay flex-1" onClick={() => void sendOffer()} disabled={busy}>Send offer</button>
      </div>
    </div>
  );
}
