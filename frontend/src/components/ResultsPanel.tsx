"use client";

import { useCallback, useEffect, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeKatex from "rehype-katex";
import {
  AlertCircle,
  Check,
  ClipboardCopy,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Square,
  Star,
  TrendingUp,
  Volume2,
} from "lucide-react";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import type { ExplainResponse } from "@/lib/types";
import { useTextToSpeech } from "@/lib/useTextToSpeech";
import { Badge } from "@/components/ui/badge";
import { GlassCard } from "./GlassCard";

type ResultsPanelProps = {
  result: ExplainResponse | null;
  loading: boolean;
  error: string;
  onRetry?: () => void;
  ttsRate?: number;
  geminiKey?: string;
  isFavorite?: boolean;
  onFavoriteToggle?: () => void;
};

function buildExportText(result: import("@/lib/types").ExplainResponse): string {
  const lines: string[] = [
    `KAP Okuryazar — ${result.company}`,
    "=".repeat(50),
    "",
    result.summary,
    "",
  ];
  if (result.notifications.length > 0) {
    lines.push("── Bildirimler ──");
    for (const n of result.notifications) {
      lines.push(`\n[${n.date ?? ""}] ${n.title}`);
      if (n.plainText) lines.push(n.plainText);
      if (n.url) lines.push(n.url);
    }
    lines.push("");
  }
  if (result.anomalies.length > 0) {
    lines.push("── Dikkat Noktaları ──");
    for (const a of result.anomalies) {
      lines.push(`${a.icon} ${a.title}: ${a.description}`);
    }
    lines.push("");
  }
  lines.push(result.disclaimer);
  lines.push(`\nOluşturulma: ${new Date().toLocaleString("tr-TR")}`);
  return lines.join("\n");
}

const LOADING_STEPS = [
  "KAP'tan bildirimler alınıyor...",
  "Bildirimler analiz ediliyor...",
  "Yapay zeka sadeleştiriyor...",
  "Neredeyse hazır...",
];

const summaryMarkdownComponents: Components = {
  h2: ({ children }) => <h2 className="mt-5 first:mt-0 text-lg font-semibold leading-tight text-ink sm:text-xl">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-4 first:mt-0 text-base font-semibold leading-tight text-ink">{children}</h3>,
  p: ({ children }) => <p className="my-3 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-5">{children}</ol>,
  li: ({ children }) => <li className="pl-1">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
  table: ({ children }) => <div className="my-4 overflow-x-auto"><table className="w-full border-collapse text-sm">{children}</table></div>,
  th: ({ children }) => <th className="border border-white/60 bg-white/55 px-3 py-2 text-left font-semibold text-ink">{children}</th>,
  td: ({ children }) => <td className="border border-white/60 px-3 py-2">{children}</td>,
  code: ({ children }) => <code className="rounded bg-ink/5 px-1 py-0.5 text-[0.92em]">{children}</code>,
};

const compactMarkdownComponents: Components = {
  h2: ({ children }) => <h2 className="mt-3 first:mt-0 text-sm font-semibold text-ink">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-2 first:mt-0 text-sm font-semibold text-ink">{children}</h3>,
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
  li: ({ children }) => <li className="pl-1">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
  code: ({ children }) => <code className="rounded bg-ink/5 px-1 py-0.5 text-[0.92em]">{children}</code>,
};

export function ResultsPanel({ result, loading, error, onRetry, ttsRate = 0.92, geminiKey, isFavorite = false, onFavoriteToggle }: ResultsPanelProps) {
  const tts = useTextToSpeech("tr-TR", ttsRate, geminiKey);
  const [loadingStep, setLoadingStep] = useState(0);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!loading) {
      setLoadingStep(0);
      return;
    }
    const intervals = [0, 3000, 8000, 18000];
    const timers = intervals.map((delay, idx) =>
      setTimeout(() => setLoadingStep(idx), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [loading]);

  const handleSpeak = useCallback(() => {
    if (result) tts.speak(result.summary);
  }, [result, tts]);

  const handleCopy = useCallback(async () => {
    if (!result) return;
    const text = buildExportText(result);
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [result]);

  const handleExport = useCallback(() => {
    if (!result) return;
    const text = buildExportText(result);
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.company.replace(/\s+/g, "_")}_KAP.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result]);

  if (loading) {
    return (
      <GlassCard className="mx-auto mt-10 w-full max-w-4xl p-7 animate-fade-in" aria-live="polite" aria-busy="true">
        <div className="flex items-center gap-3 text-sm font-medium text-ink-soft">
          <Loader2 className="h-5 w-5 animate-spin text-iris-indigo" aria-hidden />
          <span aria-live="polite" aria-atomic="true">
            {LOADING_STEPS[loadingStep]}
          </span>
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
        <div className="min-w-0 flex-1 space-y-1">
          <h2 className="font-semibold text-ink">Analiz hazırlanamadı</h2>
          <p className="text-sm leading-6 text-ink-muted">{error}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-iris-indigo hover:underline"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden />
              Tekrar dene
            </button>
          )}
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
        <div className="flex items-center gap-2">
          {tts.isSupported && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={
                  tts.isSpeaking
                    ? tts.isPaused
                      ? tts.resume
                      : tts.pause
                    : handleSpeak
                }
                aria-label={
                  tts.isSpeaking
                    ? tts.isPaused
                      ? "Okumaya devam et"
                      : "Okumayı duraklat"
                    : tts.isGemini
                      ? "Gemini sesiyle oku"
                      : "Metni sesli oku"
                }
                title={tts.isGemini ? "Gemini AI sesi" : "Tarayıcı sesi"}
                className={`grid h-9 w-9 place-items-center rounded-lg shadow-glass-soft transition hover:bg-white ${tts.isGemini ? "bg-iris-indigo/10 text-iris-indigo" : "bg-white/70 text-iris-indigo"}`}
              >
                {tts.isSpeaking && !tts.isPaused ? (
                  <Pause className="h-4 w-4" aria-hidden />
                ) : tts.isSpeaking && tts.isPaused ? (
                  <Play className="h-4 w-4" aria-hidden />
                ) : (
                  <Volume2 className="h-4 w-4" aria-hidden />
                )}
              </button>
              {geminiKey && !tts.isSpeaking && (
                <span className="hidden sm:inline text-[10px] font-semibold text-iris-indigo bg-iris-indigo/10 px-1.5 py-0.5 rounded-full">
                  Gemini
                </span>
              )}
            </div>
          )}
          {tts.isSpeaking && (
            <button
              type="button"
              onClick={tts.stop}
              aria-label="Okumayı durdur"
              className="grid h-9 w-9 place-items-center rounded-lg bg-white/70 text-rose-500 shadow-glass-soft transition hover:bg-white"
            >
              <Square className="h-4 w-4" aria-hidden />
            </button>
          )}
          <Badge variant={sourceVariant}>{sourceLabel}</Badge>
          {result.disclosureCount != null && (
            <span className="text-[11px] text-ink-muted">
              {result.disclosureCount} bildirim
            </span>
          )}
          {result.responseTimeMs != null && (
            <span className="text-[11px] text-ink-muted tabular-nums" title="Yanıt süresi">
              {(result.responseTimeMs / 1000).toFixed(1)}s
            </span>
          )}
          {onFavoriteToggle && (
            <button
              type="button"
              onClick={onFavoriteToggle}
              aria-label={isFavorite ? "Favoriden çıkar" : "Favorilere ekle"}
              title={isFavorite ? "Favoriden çıkar" : "Favorilere ekle"}
              className="grid h-9 w-9 place-items-center rounded-lg bg-white/70 dark:bg-white/10 shadow-glass-soft transition hover:bg-white dark:hover:bg-white/20"
            >
              <Star
                className={`h-4 w-4 transition-colors ${isFavorite ? "fill-amber-400 text-amber-400" : "text-ink-muted"}`}
                aria-hidden
              />
            </button>
          )}
          <button
            type="button"
            onClick={() => void handleCopy()}
            aria-label={copied ? "Kopyalandı" : "Özeti kopyala"}
            title={copied ? "Kopyalandı!" : "Panoya kopyala"}
            className="grid h-9 w-9 place-items-center rounded-lg bg-white/70 dark:bg-white/10 text-ink-muted shadow-glass-soft transition hover:bg-white dark:hover:bg-white/20"
          >
            {copied
              ? <Check className="h-4 w-4 text-emerald-500" aria-hidden />
              : <ClipboardCopy className="h-4 w-4" aria-hidden />}
          </button>
          <button
            type="button"
            onClick={handleExport}
            aria-label="Metin olarak indir"
            title=".txt olarak indir"
            className="grid h-9 w-9 place-items-center rounded-lg bg-white/70 dark:bg-white/10 text-ink-muted shadow-glass-soft transition hover:bg-white dark:hover:bg-white/20"
          >
            <Download className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </header>

      <div className="mt-6 text-base leading-7 text-ink-soft sm:text-lg">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeKatex]}
          skipHtml
          components={summaryMarkdownComponents}
        >
          {result.summary}
        </ReactMarkdown>
      </div>

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
                <div className="mt-2 text-sm leading-6 text-ink-muted">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    skipHtml
                    components={compactMarkdownComponents}
                  >
                    {item.plainText}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>

      <p className="mt-6 text-xs leading-5 text-ink-muted">{result.disclaimer}</p>
    </GlassCard>
  );
}
