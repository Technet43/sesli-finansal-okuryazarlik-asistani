import { AlertCircle, ExternalLink, FileText, Loader2, TrendingUp } from "lucide-react";
import type { ExplainResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { GlassCard } from "./GlassCard";

type ResultsPanelProps = {
  result: ExplainResponse | null;
  loading: boolean;
  error: string;
};

export function ResultsPanel({ result, loading, error }: ResultsPanelProps) {
  if (loading) {
    return (
      <GlassCard className="mx-auto mt-10 w-full max-w-4xl p-7 animate-fade-in">
        <div className="flex items-center gap-3 text-sm font-medium text-ink-soft">
          <Loader2 className="h-5 w-5 animate-spin text-iris-indigo" aria-hidden />
          KAP bildirimleri sadeleştiriliyor
        </div>
        <div className="mt-7 space-y-3">
          <div className="shimmer h-5 w-2/3 animate-shimmer rounded-full" />
          <div className="shimmer h-4 w-full animate-shimmer rounded-full" />
          <div className="shimmer h-4 w-5/6 animate-shimmer rounded-full" />
        </div>
        <div className="mt-8 grid gap-3">
          {[0, 1, 2].map((index) => (
            <div
              key={index}
              className="rounded-2xl border border-white/60 bg-white/45 p-5"
            >
              <div className="shimmer h-3.5 w-24 animate-shimmer rounded-full" />
              <div className="shimmer mt-3 h-4 w-2/3 animate-shimmer rounded-full" />
              <div className="shimmer mt-2 h-3 w-full animate-shimmer rounded-full" />
            </div>
          ))}
        </div>
      </GlassCard>
    );
  }

  if (error) {
    return (
      <GlassCard className="mx-auto mt-10 flex w-full max-w-4xl gap-4 p-6 animate-fade-in">
        <AlertCircle className="h-6 w-6 shrink-0 text-rose-500" aria-hidden />
        <div className="space-y-1">
          <h2 className="font-semibold text-ink">Analiz hazırlanamadı</h2>
          <p className="text-sm leading-6 text-ink-muted">{error}</p>
        </div>
      </GlassCard>
    );
  }

  if (!result) {
    return null;
  }

  const sourceLabel = result.source === "demo" ? "Demo" : "KAP";
  const sourceVariant = result.source === "demo" ? "warning" : "live";

  return (
    <GlassCard className="mx-auto mt-10 w-full max-w-4xl p-7 text-left animate-fade-in">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-iris-indigo">
            Sonuç
          </p>
          <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-[28px]">
            {result.company}
          </h2>
        </div>
        <Badge variant={sourceVariant}>{sourceLabel}</Badge>
      </header>

      <p className="mt-6 text-base leading-7 text-ink-soft sm:text-lg">
        {result.summary}
      </p>

      {result.anomalies && result.anomalies.length > 0 ? (
        <div className="mt-7 space-y-3">
          {result.anomalies.map((flag) => (
            <div
              key={flag.title}
              className="rounded-2xl border border-amber-200/70 bg-amber-50/80 p-4 shadow-glass-soft backdrop-blur"
            >
              <div className="flex items-start gap-3">
                <span className="text-xl leading-none">{flag.icon}</span>
                <div className="min-w-0 flex-1">
                  <h4 className="font-semibold text-amber-900">{flag.title}</h4>
                  <p className="mt-1 text-sm leading-5 text-amber-800">
                    {flag.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {result.financialNumbers && result.financialNumbers.length > 0 ? (
        <div className={`${result.anomalies && result.anomalies.length > 0 ? "mt-6" : "mt-7"} rounded-2xl border border-white/65 bg-white/55 p-5 shadow-glass-soft backdrop-blur`}>
          <div className="flex items-center gap-3 mb-4">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white text-emerald-600 shadow-[0_8px_22px_-14px_rgba(16,185,129,0.45)]">
              <TrendingUp className="h-4 w-4" aria-hidden />
            </span>
            <h3 className="font-semibold text-ink">Finansal Rakamlar</h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {result.financialNumbers.map((num) => (
              <div key={num.label} className="rounded-lg border border-white/50 bg-white/30 p-3">
                <p className="text-xs font-medium text-ink-muted">{num.label}</p>
                <p className="mt-1 text-sm font-semibold text-iris-indigo">{num.value}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className={`${result.anomalies && result.anomalies.length > 0 ? "mt-6" : result.financialNumbers && result.financialNumbers.length > 0 ? "mt-6" : "mt-7"} grid gap-3`}>
        {result.notifications.map((item, index) => (
          <article
            key={`${item.date}-${index}`}
            className="rounded-2xl border border-white/65 bg-white/55 p-5 shadow-glass-soft backdrop-blur transition hover:-translate-y-0.5"
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white text-iris-indigo shadow-[0_8px_22px_-14px_rgba(124,92,255,0.45)]">
                <FileText className="h-4 w-4" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  {item.date ? (
                    <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                      {item.date}
                    </p>
                  ) : null}
                  {item.category ? (
                    <Badge variant="iris" className="text-xs">
                      {item.category}
                    </Badge>
                  ) : null}
                </div>
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-flex items-center gap-2 font-semibold leading-snug text-iris-indigo hover:underline"
                  >
                    {item.title}
                    <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                  </a>
                ) : (
                  <h3 className="mt-1 font-semibold leading-snug text-ink">
                    {item.title}
                  </h3>
                )}
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  {item.plainText}
                </p>
              </div>
            </div>
          </article>
        ))}
      </div>

      <p className="mt-6 text-xs leading-5 text-ink-muted">{result.disclaimer}</p>
    </GlassCard>
  );
}
