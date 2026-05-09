import { Activity, Sparkles } from "lucide-react";
import type { SystemStatus } from "@/lib/types";
import { GlassCard } from "./GlassCard";

type StatusCardsProps = {
  status: SystemStatus | null;
};

export function StatusCards({ status }: StatusCardsProps) {
  const kapLabel = status?.kap.label ?? "Canlı veri kaynağı";
  const geminiLabel = status?.gemini.label ?? "Fallback modda";
  const geminiConnected = status?.gemini.status === "connected";

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-slate-900">Sistem durumu</p>
      <div className="grid grid-cols-2 gap-3">
        <GlassCard className="p-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Activity className="h-4 w-4 text-emerald-500" />
            KAP
          </div>
          <p className="mt-2 text-xs text-slate-600">{kapLabel}</p>
        </GlassCard>
        <GlassCard className="p-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Sparkles className={geminiConnected ? "h-4 w-4 text-violet-600" : "h-4 w-4 text-slate-500"} />
            Gemini
          </div>
          <p className="mt-2 text-xs text-slate-600">{geminiLabel}</p>
        </GlassCard>
      </div>
      <p className="text-xs text-emerald-600">Son kontrol: {status?.lastCheck ?? "Az önce"}</p>
    </div>
  );
}
