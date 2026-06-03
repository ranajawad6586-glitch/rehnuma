"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Deal } from "@/lib/types";
import { humanStatus } from "@/lib/format";

export default function DealsPage() {
  const { user, loading } = useAuth();
  const [deals, setDeals] = useState<Deal[]>([]);

  useEffect(() => {
    if (user) api<Deal[]>("/deals").then(setDeals).catch(() => setDeals([]));
  }, [user]);

  if (loading) return <p className="text-ink/50">Loading…</p>;
  if (!user)
    return (
      <div className="card p-8 text-center text-ink/60">
        <a href="/verify" className="text-moss underline">Verify</a> to see your deals.
      </div>
    );

  return (
    <div className="space-y-4">
      <h1 className="font-display text-3xl text-moss">My deals</h1>
      {deals.length === 0 ? (
        <div className="card p-8 text-center text-ink/60">
          No deals yet. <Link href="/" className="text-moss underline">Browse listings</Link> to start one.
        </div>
      ) : (
        <div className="space-y-3">
          {deals.map((d) => (
            <Link key={d.id} href={`/deals/${d.id}`} className="card p-4 flex items-center justify-between hover:shadow-lift">
              <span>Deal #{d.id} · listing #{d.listing_id} · {user.id === d.tenant_id ? "as tenant" : "as owner"}</span>
              <span className="chip bg-moss/10 text-moss">{humanStatus(d.status)}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
