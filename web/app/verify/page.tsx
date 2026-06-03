"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type OtpRequestResponse = { sent: boolean; channel: string; expires_in: number; dev_code: string | null };
type TokenResponse = { access_token: string };

export default function VerifyPage() {
  const router = useRouter();
  const { user, login, refresh, logout } = useAuth();
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [cnic, setCnic] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function requestOtp() {
    setError("");
    setBusy(true);
    try {
      const res = await api<OtpRequestResponse>("/auth/otp/request", {
        method: "POST",
        auth: false,
        body: { phone, name: name || null, roles: ["tenant", "owner"] },
      });
      setDevCode(res.dev_code);
      setStep("code");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not send code.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp() {
    setError("");
    setBusy(true);
    try {
      const res = await api<TokenResponse>("/auth/otp/verify", {
        method: "POST",
        auth: false,
        body: { phone, code },
      });
      await login(res.access_token);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Invalid code.");
    } finally {
      setBusy(false);
    }
  }

  async function submitCnic() {
    setError("");
    setBusy(true);
    try {
      await api("/auth/cnic", { method: "POST", body: { cnic } });
      await refresh();
      router.push("/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save CNIC.");
    } finally {
      setBusy(false);
    }
  }

  // Phone verified already -> CNIC step (needed to open chat / publish).
  if (user) {
    return (
      <div className="max-w-md mx-auto card p-6 space-y-4">
        <h1 className="font-display text-2xl text-moss">
          {user.cnic_captured ? "You’re signed in" : "Verify your CNIC"}
        </h1>
        {user.cnic_captured ? (
          <>
            <p className="text-ink/70">
              Signed in as <strong>{user.name ?? "your account"}</strong> — fully verified ✓.
            </p>
            <a href="/" className="btn-primary w-full">Browse listings</a>
            <button
              className="btn-ghost w-full"
              onClick={() => { logout(); setStep("phone"); }}
            >
              Log out / sign up with a different number
            </button>
          </>
        ) : (
          <>
            <p className="text-sm text-ink/70">
              Phone verified ✓. Add your CNIC to open chats with owners and generate agreements.
              It’s stored hashed and never shown to anyone.
            </p>
            <div>
              <label className="label">CNIC</label>
              <input className="input" value={cnic} placeholder="61101-1234567-1"
                onChange={(e) => setCnic(e.target.value)} />
            </div>
            {error && <p className="text-sm text-clay-dark">{error}</p>}
            <button className="btn-primary w-full" onClick={() => void submitCnic()} disabled={busy}>
              Save CNIC
            </button>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto card p-6 space-y-4">
      <h1 className="font-display text-2xl text-moss">Log in or sign up</h1>
      <p className="text-sm text-ink/70">
        No passwords — we send a one-time code over WhatsApp. New here? This creates your account.
        Returning? It logs you in. Your number is stored encrypted and stays private.
      </p>

      {step === "phone" ? (
        <>
          <div>
            <label className="label">Name (optional)</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Phone</label>
            <input className="input" value={phone} placeholder="03001234567"
              onChange={(e) => setPhone(e.target.value)} />
          </div>
          {error && <p className="text-sm text-clay-dark">{error}</p>}
          <button className="btn-primary w-full" onClick={() => void requestOtp()} disabled={busy}>
            Send code
          </button>
        </>
      ) : (
        <>
          {devCode && (
            <p className="text-xs rounded-lg bg-clay/10 text-clay-dark px-3 py-2">
              Dev mode: your code is <strong>{devCode}</strong> (no WhatsApp key configured).
            </p>
          )}
          <div>
            <label className="label">Enter code</label>
            <input className="input tracking-widest" value={code} placeholder="6-digit code"
              onChange={(e) => setCode(e.target.value)} />
          </div>
          {error && <p className="text-sm text-clay-dark">{error}</p>}
          <button className="btn-primary w-full" onClick={() => void verifyOtp()} disabled={busy}>
            Verify
          </button>
          <button className="btn-ghost w-full" onClick={() => setStep("phone")}>Back</button>
        </>
      )}
    </div>
  );
}
