"use client";

import { useCallback, useState } from "react";
import {
  AlertCircle,
  Check,
  ClipboardCopy,
  ExternalLink,
  FileText,
  Loader2,
  RefreshCw,
  TrendingUp,
  Volume2,
  Pause,
  Play,
  Square,
} from "lucide-react";
import type { ExplainResponse } from "@/lib/types";
import { useTextToSpeech } from "@/lib/useTextToSpeech";
import { Badge } from "@/components/ui/badge";
import { GlassCard } from "./GlassCard";

type CompanyColumnProps = {
  label: "A" | "B";
  result: ExplainResponse | null;
  loading: boolean;
  error: string;
  onRetry?: () => void;
  ttsRate?: number;
  geminiKey?: string;
};

function CompanyColumn({ label, result, loading, error, onRetry, ttsRate = 0.92, geminiKey }: CompanyColumnProps) {
  const tts = useTextToSpeech("tr-TR", ttsRate, geminiKey);
  const [copied, setCopied] = useState(false);

  const handleSpeak = useCallback(() => {
    if (result) tts.speak(result.summary);
  }, [result, tts]);

  const handleCopy = useCallback(async () => {
    if (!result) return;
    await navigator.clipboard.writeText(`${result.company}\n\n${result.summary}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [result]);

  if (loading) {
    return (
      <GlassCard className="flex-1 p-6 animate-fade-in" aria-busy="true">
        <div className="flex items-center gap-2 text-sm text-ink-soft">
          <Loader2 className="h-4 w-4 animate-spin text-iris-indigo" />
          Analiz ediliyor...
        </div>
        <div className="mt-5 space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="shimmer h-4 animate-shimmer rounded-full" style={{ width: `${75 - i * 10}%` }} />
          ))}
        </div>
      </GlassCard>
    );
  }

  if (error) {
    return (
      <GlassCard className="flex-1 p-6 animate-fade-in">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-500" />
          <div>
            <p className="font-semibold text-ink">Hata</p>
            <p className="mt-1 text-sm text-ink-muted">{error}</p>
            {onRetry && (
              <button type="button" onClick={onRetry} className="mt-2 flex items-center gap-1 text-sm text-iris-indigo hover:underline">
                <RefreshCw className="h-3.5 w-3.5" /> Tekrar dene
              </button>
            )}
          </div>
        </div>
      </GlassCard>
    );
  }

  if (!result) {
    return (
      <GlassCard className="flex-1 p-6 flex items-center justify-center text-sm text-ink-muted">
        Şirket {label} aranıyor...
      </GlassCard>
    );
  }

  return (
    <GlassCard className="flex-1 p-6 animate-fade-in">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-iris-indigo">Şirket {label}</p>
          <h3 className="mt-1 text-xl font-semibold tracking-tight text-ink">{result.company}</h3>
        </div>
        <div className="flex items-center gap-2">
          {tts.isSupported && (
            <button
              type="button"
              onClick={tts.isSpeaking ? (tts.isPaused ? tts.resume : tts.pause) : handleSpeak}
              aria-label={tts.isSpeaking ? (tts.isPaused ? "Devam et" : "Duraklat") : "Sesli oku"}
              className="grid h-8 w-8 place-items-center rounded-lg bg-white/70 text-iris-indigo shadow-glass-soft transition hover:bg-white"
            >
              {tts.isSpeaking && !tts.isPaused ? <Pause className="h-3.5 w-3.5" /> : tts.isSpeaking ? <Play className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
            </button>
          )}
          {tts.isSpeaking && (
            <button type="button" onClick={tts.stop} aria-label="Durdur" className="grid h-8 w-8 place-items-center rounded-lg bg-white/70 text-rose-500 shadow-glass-soft transition hover:bg-white">
              <Square className="h-3.5 w-3.5" />
            </button>
          )}
          <Badge variant={result.source === "demo" ? "warning" : "live"}>{result.source === "demo" ? "Demo" : "KAP"}</Badge>
          <button type="button" onClick={() => void handleCopy()} aria-label="Kopyala" className="grid h-8 w-8 place-items-center rounded-lg bg-white/70 text-ink-muted shadow-glass-soft transition hover:bg-white">
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <ClipboardCopy className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      <p className="mt-4 text-sm leading-7 text-ink-soft">{result.summary}</p>

      {result.anomalies.length > 0 && (
        <div className="mt-4 space-y-2">
          {result.anomalies.map((a) => (
            <div key={a.title} className="flex items-start gap-2 rounded-xl border border-amber-200/70 bg-amber-50/80 p-3 text-xs">
              <span>{a.icon}</span>
              <div>
                <span className="font-semibold text-amber-900">{a.title}</span>
                <span className="ml-1 text-amber-800">{a.description}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {result.financialNumbers.length > 0 && (
        <div className="mt-4 rounded-xl border border-white/65 bg-white/55 p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="h-4 w-4 text-emerald-600" />
            <span className="text-sm font-semibold text-ink">Finansal Rakamlar</span>
          </div>
          <div className="grid gap-2 grid-cols-2">
            {result.financialNumbers.slice(0, 6).map((n) => (
              <div key={n.label} className="rounded-lg border border-white/50 bg-white/30 p-2">
                <p className="text-[10px] font-medium text-ink-muted">{n.label}</p>
                <p className="text-xs font-semibold text-iris-indigo">{n.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 space-y-2">
        {result.notifications.slice(0, 4).map((item, i) => (
          <article key={`${item.date}-${i}`} className="rounded-xl border border-white/65 bg-white/55 p-4">
            <div className="flex items-start gap-2">
              <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white text-iris-indigo shadow-sm">
                <FileText className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0 flex-1">
                {item.date && <p className="text-[10px] font-medium uppercase tracking-wide text-ink-muted">{item.date}</p>}
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="mt-0.5 flex items-center gap-1 text-sm font-semibold text-iris-indigo hover:underline">
                    {item.title} <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                ) : (
                  <p className="mt-0.5 text-sm font-semibold text-ink">{item.title}</p>
                )}
                <p className="mt-1 text-xs leading-5 text-ink-muted">{item.plainText}</p>
              </div>
            </div>
          </article>
        ))}
      </div>

      <p className="mt-4 text-[10px] leading-5 text-ink-muted">{result.disclaimer}</p>
    </GlassCard>
  );
}

type ComparisonPanelProps = {
  resultA: ExplainResponse | null;
  resultB: ExplainResponse | null;
  loadingA: boolean;
  loadingB: boolean;
  errorA: string;
  errorB: string;
  onRetryA?: () => void;
  onRetryB?: () => void;
  ttsRate?: number;
  geminiKey?: string;
};

function DiffBadge({ a, b }: { a: number; b: number }) {
  if (a === 0 || b === 0) return null;
  const ratio = ((b - a) / a) * 100;
  const label = ratio > 0 ? `B +${ratio.toFixed(0)}%` : `B ${ratio.toFixed(0)}%`;
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${ratio > 0 ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
      {label}
    </span>
  );
}

export function ComparisonPanel({
  resultA,
  resultB,
  loadingA,
  loadingB,
  errorA,
  errorB,
  onRetryA,
  onRetryB,
  ttsRate,
  geminiKey,
}: ComparisonPanelProps) {
  const showDiff = resultA && resultB &&
    resultA.disclosureCount != null && resultB.disclosureCount != null;

  return (
    <div className="mx-auto mt-10 w-full max-w-[1200px] space-y-4 animate-fade-in">
      {showDiff && (
        <div className="flex items-center justify-center gap-3 text-sm text-ink-muted">
          <span className="font-medium text-ink">{resultA!.company}</span>
          <span>vs</span>
          <span className="font-medium text-ink">{resultB!.company}</span>
          <DiffBadge a={resultA!.disclosureCount!} b={resultB!.disclosureCount!} />
        </div>
      )}
      <div className="flex flex-col gap-6 lg:flex-row">
        <CompanyColumn
          label="A"
          result={resultA}
          loading={loadingA}
          error={errorA}
          onRetry={onRetryA}
          ttsRate={ttsRate}
          geminiKey={geminiKey}
        />
        <CompanyColumn
          label="B"
          result={resultB}
          loading={loadingB}
          error={errorB}
          onRetry={onRetryB}
          ttsRate={ttsRate}
          geminiKey={geminiKey}
        />
      </div>
    </div>
  );
}
