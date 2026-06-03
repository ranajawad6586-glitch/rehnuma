import type { Metadata } from "next";
import { Fraunces, Outfit } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { Nav } from "@/components/Nav";

const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit", display: "swap" });

export const metadata: Metadata = {
  title: "RehnumaRent — direct rentals in Bahria Town Islamabad",
  description: "Verified listings, a neutral AI realtor, and a structured deal pipeline. No dealer.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${outfit.variable}`}>
      <body>
        <AuthProvider>
          <Nav />
          <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
          <footer className="mx-auto max-w-5xl px-4 py-10 text-xs text-ink/50">
            RehnumaRent · MVP · Bahria Town Islamabad only · dealer-free by design
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
