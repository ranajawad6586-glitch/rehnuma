import Link from "next/link";
import type { Listing } from "@/lib/types";
import { formatPKR, shortAddress, sizeLabel } from "@/lib/format";
import { ListingImage } from "@/components/ListingImage";

export function ListingCard({ listing }: { listing: Listing }) {
  return (
    <Link href={`/listings/${listing.id}`} className="group card overflow-hidden hover:shadow-lift transition block">
      <div className="relative">
        <ListingImage photos={listing.photos} phase={listing.phase} id={listing.id}
          className="h-40 w-full object-cover" />
        <span className="absolute bottom-2 left-2 chip bg-black/55 text-paper text-[11px]">📍 {listing.phase}</span>
      </div>
      <div className="p-5">
      <div className="flex items-start justify-between gap-3">
        <span className="chip bg-moss/10 text-moss">{sizeLabel(listing.size)}</span>
        <span className="chip bg-clay/10 text-clay-dark">{listing.phase}</span>
      </div>
      <div className="mt-3 font-display text-2xl font-semibold text-moss">
        {formatPKR(listing.rent)}
        <span className="text-sm font-body font-normal text-ink/50"> / month</span>
      </div>
      <div className="mt-1 text-sm text-ink/70">{shortAddress(listing)}</div>
      <div className="mt-3 flex gap-4 text-sm text-ink/60">
        <span>{listing.beds} beds</span>
        <span>{listing.baths} baths</span>
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-paper-deep pt-3">
        <span className="trust">✓ Verified · Direct owner</span>
        <span className="text-sm font-medium text-clay-dark group-hover:underline">View &amp; chat →</span>
      </div>
      </div>
    </Link>
  );
}
