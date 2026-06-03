"use client";

import { useState } from "react";
import { placeImage } from "@/lib/placeImage";

// Prefer the listing's real photo; if it fails to load (e.g. CDN hotlink block), fall back to
// satellite imagery of the phase so a card never shows a broken image.
export function ListingImage({
  photos,
  phase,
  id,
  className,
}: {
  photos: string[];
  phase: string;
  id: number;
  className?: string;
}) {
  const fallback = placeImage(phase, id);
  const [src, setSrc] = useState(photos?.[0] || fallback);
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={`${phase} property`}
      className={className}
      loading="lazy"
      onError={() => {
        if (src !== fallback) setSrc(fallback);
      }}
    />
  );
}
