"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function Nav() {
  const { user, logout } = useAuth();
  return (
    <header className="border-b border-paper-deep bg-paper/80 backdrop-blur sticky top-0 z-20">
      <nav className="mx-auto max-w-5xl px-4 py-3 flex items-center gap-5">
        <Link href="/" className="font-display text-xl font-semibold text-moss">
          Rehnuma<span className="text-clay">Rent</span>
        </Link>
        <div className="flex-1" />
        <Link href="/" className="text-sm text-ink/70 hover:text-moss">Listings</Link>
        <Link href="/rehnuma" className="text-sm text-ink/70 hover:text-moss">Rehnuma</Link>
        <Link href="/list-property" className="text-sm text-ink/70 hover:text-moss">List a property</Link>
        {user ? (
          <>
            <Link href="/deals" className="text-sm text-ink/70 hover:text-moss">My deals</Link>
            <button onClick={logout} className="text-sm text-ink/50 hover:text-clay" title={user.name ?? "account"}>
              Log out
            </button>
          </>
        ) : (
          <Link href="/verify" className="btn-primary !py-1.5 !px-4">Log in / Sign up</Link>
        )}
      </nav>
    </header>
  );
}
