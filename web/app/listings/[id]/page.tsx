"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Deal, Listing } from "@/lib/types";
import { formatPKR, shortAddress, sizeLabel } from "@/lib/format";
import { ListingImage } from "@/components/ListingImage";
import { RehnumaChat } from "@/components/RehnumaChat";

export default function ListingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Listing>(`/listings/${id}`, { auth: false })
      .then(setListing)
      .catch(() => setError("This listing is not available."));
  }, [id]);

  async function startInquiry() {
    if (!user) {
      router.push("/verify");
      return;
    }
    setBusy(true);
    try {
      const deal = await api<Deal>("/deals", { method: "POST", body: { listing_id: Number(id) } });
      router.push(`/deals/${deal.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start inquiry.");
      setBusy(false);
    }
  }

  if (error) return <div className="card p-8 text-center text-ink/60">{error}</div>;
  if (!listing) return <p className="text-ink/50">Loading…</p>;

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="space-y-4">
        <div className="card overflow-hidden">
          <div className="relative">
            <ListingImage photos={listing.photos} phase={listing.phase} id={listing.id}
              className="h-56 w-full object-cover" />
            <span className="absolute bottom-2 left-2 chip bg-black/55 text-paper">📍 {listing.phase}</span>
          </div>
          <div className="p-6">
          <div className="flex gap-2">
            <span className="chip bg-moss/10 text-moss">{sizeLabel(listing.size)}</span>
            <span className="chip bg-clay/10 text-clay-dark">{listing.phase}</span>
            <span className="chip bg-moss/10 text-moss">Verified plot</span>
          </div>
          <div className="mt-4 font-display text-4xl font-semibold text-moss">
            {formatPKR(listing.rent)}
            <span className="text-base font-body font-normal text-ink/50"> / month</span>
          </div>
          <p className="mt-2 text-ink/75">{shortAddress(listing)}</p>
          <div className="mt-4 flex gap-6 text-sm text-ink/70">
            <span>🛏 {listing.beds} beds</span>
            <span>🛁 {listing.baths} baths</span>
          </div>

          {/* Honest anchoring: name the dealer fee you avoid (one month's rent each side). */}
          <div className="mt-5 rounded-xl bg-moss/10 px-4 py-3 text-sm text-moss-dark">
            Going direct, you skip the dealer&rsquo;s commission — roughly{" "}
            <strong>{formatPKR(listing.rent)}</strong> (one month&rsquo;s rent). You pay the owner, nothing to us.
          </div>

          <button className="btn-clay mt-5 w-full text-base !py-3.5" onClick={() => void startInquiry()} disabled={busy}>
            {user ? "Chat the owner directly →" : "Verify & chat the owner →"}
          </button>
          <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-xs text-ink/55">
            <span aria-hidden>🔒</span> Takes ~30 seconds · your number is encrypted and stays private until you both agree to share.
          </p>
          </div>
        </div>
      </div>
      <RehnumaChat listingId={listing.id} />
    </div>
  );
}
