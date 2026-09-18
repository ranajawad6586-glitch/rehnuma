"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, getToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Listing } from "@/lib/types";

// The address space comes from the server (GET /listings/grid) so these choices can never
// drift from the seeded Bahria grid — a mismatch here is rejected on submit.
type Group = { label: string; areas: string[] };
type Bounds = { max_street: number; max_house: number };
type Grid = {
  phases: number[];
  areas_by_phase: Record<string, string[]>;
  groups_by_phase: Record<string, Group[]>;
  area_phases: number[];
  postal_codes: Record<string, string>;
  bounds_by_phase: Record<string, Bounds>;
  sizes: string[];
};
const FALLBACK_GRID: Grid = {
  phases: [8], areas_by_phase: { "8": [] }, groups_by_phase: { "8": [] },
  area_phases: [8], postal_codes: {}, bounds_by_phase: {}, sizes: ["10-marla"],
};

export default function ListPropertyPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [grid, setGrid] = useState<Grid | null>(null);
  const [form, setForm] = useState({ phase: "4", sector: "", street: "", house_ref: "", size: "10-marla", rent: "", beds: "3", baths: "3" });
  const [pending, setPending] = useState<File[]>([]); // photos chosen before the listing exists
  const [created, setCreated] = useState<Listing | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set<K extends keyof typeof form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  useEffect(() => {
    api<Grid>("/listings/grid", { auth: false })
      .then((g) => {
        setGrid(g);
        // Areas are per-phase and most phases have none, so seed a valid pair.
        setForm((f) => ({ ...f, sector: g.areas_by_phase[f.phase]?.[0] ?? "" }));
      })
      .catch(() => setGrid(FALLBACK_GRID));
  }, []);

  const g = grid ?? FALLBACK_GRID;
  const areas = g.areas_by_phase[form.phase] ?? [];
  const groups = g.groups_by_phase[form.phase] ?? [];
  const hasAreas = areas.length > 0;

  // Changing phase must reset the area: only Phase 8 has them, and "Umer Block" is Phase 8 only.
  function setPhase(v: string) {
    const next = g.areas_by_phase[v] ?? [];
    setForm((f) => ({ ...f, phase: v, sector: next.includes(f.sector) ? f.sector : (next[0] ?? "") }));
  }

  // Show the owner the address they are declaring, as a resident would write it.
  const addressPreview = [
    form.house_ref && `House ${form.house_ref}`,
    form.street && (/^\d/.test(form.street.trim()) ? `Street ${form.street.trim()}` : form.street.trim()),
    hasAreas ? form.sector : "",
    `Phase ${form.phase}`,
    "Bahria Town, Rawalpindi",
  ].filter(Boolean).join(", ");

  async function uploadTo(listingId: number, files: File[]): Promise<Listing> {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    const token = getToken();
    const res = await fetch(`/api/listings/${listingId}/photos`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error((d as { detail?: string }).detail ?? "Photo upload failed");
    }
    return res.json();
  }

  async function create() {
    setError("");
    setBusy(true);
    try {
      let listing = await api<Listing>("/listings", {
        method: "POST",
        body: {
          phase: Number(form.phase),
          sector: hasAreas ? form.sector : "",
          street: form.street,
          house_ref: form.house_ref,
          size: form.size,
          rent: Number(form.rent),
          beds: Number(form.beds),
          baths: Number(form.baths),
          photos: [],
        },
      });
      // Attach any photos chosen on the form.
      if (pending.length > 0) {
        listing = await uploadTo(listing.id, pending);
        setPending([]);
      }
      setCreated(listing);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Could not create listing.");
    } finally {
      setBusy(false);
    }
  }

  async function uploadPhotos(files: FileList | null) {
    if (!created || !files || files.length === 0) return;
    setError("");
    setBusy(true);
    try {
      setCreated(await uploadTo(created.id, Array.from(files)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    if (!created) return;
    setError("");
    setBusy(true);
    try {
      const live = await api<Listing>(`/listings/${created.id}/publish`, { method: "POST" });
      setCreated(live);
      if (live.status === "LIVE") router.push(`/listings/${live.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not publish.");
    } finally {
      setBusy(false);
    }
  }

  if (!user)
    return (
      <div className="card p-8 text-center text-ink/60">
        <a href="/verify" className="text-moss underline">Verify</a> to list a property.
      </div>
    );

  return (
    <div className="max-w-lg mx-auto card p-6 space-y-4">
      <h1 className="font-display text-2xl text-moss">List your property</h1>
      <p className="text-sm text-ink/70">
        We match the plot against the Bahria grid. It only goes LIVE after you’re CNIC-verified.
      </p>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Phase</label>
          <select className="input" value={form.phase} onChange={(e) => setPhase(e.target.value)}>
            {g.phases.map((p) => <option key={p} value={p}>Phase {p}</option>)}
          </select>
        </div>
        {hasAreas && (
          <div>
            <label className="label">Sector / Block</label>
            <select className="input" value={form.sector} onChange={(e) => set("sector", e.target.value)}>
              {groups.length > 1
                ? groups.map((gr) => (
                    <optgroup key={gr.label} label={gr.label}>
                      {gr.areas.map((a) => <option key={a} value={a}>{a}</option>)}
                    </optgroup>
                  ))
                : areas.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
        )}
        <div>
          <label className="label">Street</label>
          <input className="input" value={form.street} placeholder="e.g. 13" onChange={(e) => set("street", e.target.value)} />
        </div>
        <div>
          <label className="label">House number</label>
          <input className="input" value={form.house_ref} placeholder="e.g. 129" onChange={(e) => set("house_ref", e.target.value)} />
          {!hasAreas && (
            <p className="mt-1 text-xs opacity-60">Phase {form.phase} has no sectors — street and house number are the address.</p>
          )}
        </div>
        <div className="sm:col-span-2 rounded-lg border border-moss/20 bg-paper/60 px-3 py-2">
          <span className="label">Your property address</span>
          <p className="font-medium">{addressPreview}</p>
          {g.postal_codes[form.phase] && (
            <p className="text-xs opacity-60">Postal code {g.postal_codes[form.phase]}</p>
          )}
          <p className="mt-1 text-xs opacity-60">
            We check this address is well-formed for Bahria Town. We can&apos;t confirm ownership
            from it — that comes from your CNIC and phone verification.
          </p>
        </div>
        <div>
          <label className="label">Size</label>
          <select className="input" value={form.size} onChange={(e) => set("size", e.target.value)}>
            {g.sizes.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Rent / month</label>
          <input className="input" type="number" value={form.rent} onChange={(e) => set("rent", e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="label">Beds</label>
            <input className="input" type="number" value={form.beds} onChange={(e) => set("beds", e.target.value)} />
          </div>
          <div>
            <label className="label">Baths</label>
            <input className="input" type="number" value={form.baths} onChange={(e) => set("baths", e.target.value)} />
          </div>
        </div>
      </div>

      {!created && (
        <div>
          <label className="label">Photos of your property</label>
          {pending.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
              {pending.map((f, i) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={i} src={URL.createObjectURL(f)} alt="selected" className="h-16 w-20 rounded-lg object-cover" />
              ))}
            </div>
          )}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={(e) => setPending(Array.from(e.target.files ?? []))}
            className="block w-full text-sm text-ink/70 file:mr-3 file:rounded-full file:border-0 file:bg-moss file:px-4 file:py-2 file:text-paper hover:file:bg-moss-dark"
          />
          <p className="mt-1 text-xs text-ink/50">JPEG/PNG/WebP, up to 5 MB each. They attach when you create the listing.</p>
        </div>
      )}

      {error && <p className="text-sm text-clay-dark">{error}</p>}

      {!created ? (
        <button className="btn-primary w-full" onClick={() => void create()} disabled={busy}>
          {pending.length > 0 ? `Match plot & create (with ${pending.length} photo${pending.length > 1 ? "s" : ""})` : "Match plot & create"}
        </button>
      ) : (
        <div className="space-y-3">
          <div className="rounded-xl bg-moss/10 px-4 py-3 text-sm text-moss-dark">
            Plot matched ✓ — listing #{created.id} is <strong>{created.status}</strong>.
          </div>

          {/* Photo upload */}
          <div>
            <label className="label">Photos of your property</label>
            {created.photos.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-2">
                {created.photos.map((p) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img key={p} src={p} alt="listing" className="h-16 w-20 rounded-lg object-cover" />
                ))}
              </div>
            )}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              onChange={(e) => void uploadPhotos(e.target.files)}
              className="block w-full text-sm text-ink/70 file:mr-3 file:rounded-full file:border-0 file:bg-moss file:px-4 file:py-2 file:text-paper hover:file:bg-moss-dark"
            />
            <p className="mt-1 text-xs text-ink/50">JPEG/PNG/WebP, up to 5 MB each. Real photos get more inquiries.</p>
          </div>

          {created.status !== "LIVE" && (
            <>
              {!user.cnic_captured && (
                <p className="text-sm text-ink/70">
                  Add your CNIC to publish. <a href="/verify" className="text-moss underline">Verify CNIC →</a>
                </p>
              )}
              <button className="btn-clay w-full" onClick={() => void publish()} disabled={busy || !user.cnic_captured}>
                Publish (go LIVE)
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
