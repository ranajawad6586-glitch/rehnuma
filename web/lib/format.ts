// Pure display helpers — unit-tested (see lib/format.test.ts).

export function formatPKR(amount: number): string {
  return `Rs ${amount.toLocaleString("en-PK")}`;
}

export function sizeLabel(size: string): string {
  // "10-marla" -> "10 Marla", "2.5-kanal" -> "2.5 Kanal"; unknown forms returned as-is.
  const m = size.match(/^([\d.]+)-(marla|kanal)$/);
  if (!m) return size;
  return `${m[1]} ${m[2].charAt(0).toUpperCase()}${m[2].slice(1)}`;
}

// Human label for deal / listing status enums (e.g. "CHAT_OPEN" -> "Chat open").
export function humanStatus(status: string): string {
  const s = status.replace(/_/g, " ").toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function shortAddress(l: { house_ref: string; sector: string; phase: string }): string {
  return `House ${l.house_ref}, Sector ${l.sector}, ${l.phase}`;
}
