import { Activity, Sparkles } from "lucide-react";
import type { SystemStatus } from "@/lib/types";

type StatusCardsProps = {
  status: SystemStatus | null;
};

export function StatusCards({ status }: StatusCardsProps) {
  const kapLabel = status?.kap.label ?? "Canlı veri kaynağı";
  const aiLabel = status?.gemini.label ?? "Fallback modda";
  const kapStatus = status?.kap.status ?? "live";
  const aiConnected = status?.gemini.status === "connected";

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-ink">Sistem durumu</p>
      <div className="grid grid-cols-2 gap-3">
        <StatusTile
          icon={<Activity className="h-4 w-4 text-emerald-500" aria-hidden />}
          title="KAP"
          description={kapLabel}
          dotColor={kapStatus === "live" ? "bg-emerald-500" : "bg-amber-400"}
        />
        <StatusTile
          icon={
            <Sparkles
              className={
                aiConnected
                  ? "h-4 w-4 text-iris-indigo"
                  : "h-4 w-4 text-ink-muted"
              }
              aria-hidden
            />
          }
          title="AI"
          description={aiLabel}
          dotColor={aiConnected ? "bg-iris-indigo" : "bg-amber-400"}
        />
      </div>
      <p className="text-xs text-emerald-600">
        <span className="mr-1.5 inline-block h-1.5 w-1.5 -translate-y-0.5 rounded-full bg-emerald-500" />
        Son kontrol: {status?.lastCheck ?? "Az önce"}
      </p>
    </div>
  );
}

function StatusTile({
  icon,
  title,
  description,
  dotColor,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  dotColor: string;
}) {
  return (
    <div className="glass-soft rounded-xl p-3.5">
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} aria-hidden />
        <div className="flex items-center gap-1.5 text-sm font-semibold text-ink">
          {icon}
          {title}
        </div>
      </div>
      <p className="mt-1.5 text-[11px] leading-4 text-ink-muted">{description}</p>
    </div>
  );
}
