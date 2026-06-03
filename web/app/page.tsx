"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Listing } from "@/lib/types";
import { ListingCard } from "@/components/ListingCard";

const SIZES = ["5-marla", "10-marla", "1-kanal"];
const PHASES = [1, 2, 3, 4, 5, 6, 7, 8];

export default function HomePage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [size, setSize] = useState("");
  const [phase, setPhase] = useState("");
  const [maxRent, setMaxRent] = useState("");

  async function load() {
    setLoading(true);
    const params = new URLSearchParams();
    if (size) params.set("size", size);
    if (phase) params.set("phase", phase);
    if (maxRent) params.set("max_rent", maxRent);
    try {
      setListings(await api<Listing[]>(`/listings?${params.toString()}`, { auth: false }));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-8">
      <section className="card p-8 bg-gradient-to-br from-moss to-moss-dark text-paper">
        <span className="chip bg-clay text-paper mb-3">No dealer · No commission</span>
        <h1 className="font-display text-4xl font-semibold leading-tight">
          Rent direct. Keep the dealer&rsquo;s fee in your pocket.
        </h1>
        <p className="mt-3 max-w-xl text-paper/85">
          Plot-verified listings, verified owners, and <strong>Rehnuma</strong> — a neutral AI realtor
          that works for a fair deal, not a commission. In Bahria Town Islamabad.
        </p>
        {/* Trust strip — three quick reasons to feel safe, in trust-green on a calm field. */}
        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm text-paper/90">
          <span className="inline-flex items-center gap-2">✓ Plot-verified listings</span>
          <span className="inline-flex items-center gap-2">✓ CNIC-verified owners</span>
          <span className="inline-flex items-center gap-2">✓ Your number stays private</span>
        </div>
      </section>

      <section className="card p-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="label">Size</label>
            <select className="input" value={size} onChange={(e) => setSize(e.target.value)}>
              <option value="">Any</option>
              {SIZES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Phase</label>
            <select className="input" value={phase} onChange={(e) => setPhase(e.target.value)}>
              <option value="">Any</option>
              {PHASES.map((p) => (
                <option key={p} value={p}>Phase {p}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Max rent (PKR)</label>
            <input className="input" type="number" value={maxRent} placeholder="e.g. 200000"
              onChange={(e) => setMaxRent(e.target.value)} />
          </div>
          <button className="btn-primary" onClick={() => void load()}>Search</button>
        </div>
      </section>

      <section>
        {loading ? (
          <p className="text-ink/50">Loading verified listings…</p>
        ) : listings.length === 0 ? (
          <div className="card p-8 text-center text-ink/60">
            No LIVE listings match yet. Owners can <a className="text-moss underline" href="/list-property">list a property</a>.
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {listings.map((l) => (
              <ListingCard key={l.id} listing={l} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
