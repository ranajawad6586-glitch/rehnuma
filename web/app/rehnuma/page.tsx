import { RehnumaChat } from "@/components/RehnumaChat";

export default function RehnumaPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-display text-3xl text-moss">Rehnuma</h1>
        <p className="text-ink/70">Your neutral realtor for Bahria Town Islamabad rentals.</p>
      </div>
      <RehnumaChat />
    </div>
  );
}
