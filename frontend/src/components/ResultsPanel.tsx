import { AlertCircle, FileText, Loader2 } from "lucide-react";
import type { ExplainResponse } from "@/lib/types";
import { GlassCard } from "./GlassCard";

type ResultsPanelProps = {
  result: ExplainResponse | null;
  loading: boolean;
  error: string;
};

export function ResultsPanel({ result, loading, error }: ResultsPanelProps) {
  if (loading) {
    return (
      <GlassCard className="mx-auto mt-10 w-full max-w-5xl p-6">
        <div className="flex items-center gap-3 text-slate-700">
          <Loader2 className="h-5 w-5 animate-spin" />
          KAP bildirimleri sadeleştiriliyor
        </div>
        <div className="mt-6 space-y-3">
          <div className="h-5 w-2/3 animate-pulse rounded bg-white/70" />
          <div className="h-4 w-full animate-pulse rounded bg-white/60" />
          <div className="h-4 w-5/6 animate-pulse rounded bg-white/60" />
        </div>
      </GlassCard>
    );
  }

  if (error) {
    return (
      <GlassCard className="mx-auto mt-10 flex w-full max-w-5xl gap-4 p-6">
        <AlertCircle className="h-6 w-6 shrink-0 text-rose-500" />
        <div>
          <h2 className="font-semibold text-slate-950">Analiz hazırlanamadı</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{error}</p>
        </div>
      </GlassCard>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <GlassCard className="mx-auto mt-10 w-full max-w-5xl p-6 text-left">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-indigo-600">Sonuç</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">{result.company}</h2>
        </div>
        <span className="rounded-full border border-white/80 bg-white/70 px-3 py-1 text-sm font-semibold text-slate-700">
          {result.source.toUpperCase()}
        </span>
      </div>

      <p className="mt-5 text-lg leading-8 text-slate-700">{result.summary}</p>

      <div className="mt-6 grid gap-4">
        {result.notifications.map((item, index) => (
          <div key={`${item.date}-${index}`} className="rounded-lg border border-white/70 bg-white/54 p-5 shadow-sm">
            <div className="flex items-start gap-3">
              <FileText className="mt-1 h-5 w-5 shrink-0 text-indigo-600" />
              <div>
                <p className="text-sm font-medium text-slate-500">{item.date}</p>
                <h3 className="mt-1 font-semibold text-slate-950">{item.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{item.plainText}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="mt-5 text-sm text-slate-500">{result.disclaimer}</p>
    </GlassCard>
  );
}
