"use client";

import { useEffect } from "react";
import {
  ChevronRight,
  Clock,
  Mic,
  MicOff,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useSpeechRecognition } from "@/lib/useSpeechRecognition";
import { GlassCard } from "./GlassCard";

type HeroSearchProps = {
  company: string;
  setCompany: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  history: string[];
  onHistoryClick: (value: string) => void;
  favorites?: string[];
  onFavoriteToggle?: (value: string) => void;
  geminiKey?: string;
};

export function HeroSearch({
  company,
  setCompany,
  onSubmit,
  loading,
  history,
  onHistoryClick,
  favorites = [],
  onFavoriteToggle,
  geminiKey,
}: HeroSearchProps) {
  const speech = useSpeechRecognition("tr-TR", geminiKey);

  useEffect(() => {
    if (speech.transcript) {
      setCompany(speech.transcript);
    }
  }, [speech.transcript, setCompany]);

  const micCardLabel = !speech.isSupported
    ? "Tarayıcın mikrofon tanımayı desteklemiyor (Chrome/Edge önerilir)."
    : speech.isListening
      ? speech.isGemini
        ? "Kaydediyorum... bittiğinde durdur, Gemini Türkçe'yi tanıyacak."
        : "Dinliyorum... şirket adını söyle, bittiğinde durdur."
      : speech.isGemini
        ? "Gemini AI ile sesli tanıma — tarayıcıdan çok daha iyi Türkçe."
        : "Sesli sor, KAP Okuryazar anlayıp açıklasın.";

  function handleMicClick() {
    if (!speech.isSupported) return;
    if (speech.isListening) {
      speech.stop();
    } else {
      speech.start();
    }
  }

  return (
    <section className="mx-auto flex w-full max-w-4xl flex-col items-center text-center animate-fade-in">
      <Badge variant="iris" className="text-[13px]">
        <ShieldCheck className="h-3.5 w-3.5 text-iris-indigo" aria-hidden />
        Resmi KAP bildirimleri, sade Türkçe ile
      </Badge>

      <h1 className="mt-7 max-w-3xl text-balance text-4xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-5xl lg:text-[3.5rem]">
        Hangi şirketin haberlerini{" "}
        <span className="bg-iris-gradient bg-clip-text text-transparent">
          anlamak istiyorsun?
        </span>
      </h1>
      <p className="mt-5 max-w-2xl text-base leading-7 text-ink-muted sm:text-lg">
        Şirket adı yazarak veya sesle sor, gerisini KAP Okuryazar anlatsın.
      </p>

      <form
        className="mt-10 w-full"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label htmlFor="company-search" className="sr-only">
          Şirket adı
        </label>
        <div className="iris-glow group flex h-[68px] w-full items-center gap-4 rounded-2xl border border-white/70 bg-white/72 px-5 shadow-glass backdrop-blur-xl transition-shadow focus-within:shadow-glow">
          <Search className="h-5 w-5 shrink-0 text-ink-muted" aria-hidden />
          <input
            id="company-search"
            type="text"
            autoComplete="off"
            value={company}
            onChange={(event) => setCompany(event.target.value)}
            placeholder="Ziraat Bankası"
            className="min-w-0 flex-1 bg-transparent text-lg font-medium text-ink outline-none placeholder:text-slate-400 sm:text-xl"
          />
          {company ? (
            <button
              type="button"
              aria-label="Aramayı temizle"
              onClick={() => setCompany("")}
              className="grid h-9 w-9 place-items-center rounded-full bg-white/70 text-ink-muted shadow-sm transition hover:bg-white"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          ) : null}
        </div>

        <button
          type="button"
          onClick={handleMicClick}
          disabled={!speech.isSupported}
          aria-label={
            speech.isListening
              ? "Dinlemeyi durdur"
              : speech.isSupported
                ? "Mikrofonla söyle"
                : "Mikrofon desteklenmiyor"
          }
          aria-pressed={speech.isListening}
          className={`mt-5 flex w-full items-center gap-4 rounded-2xl border p-4 text-left shadow-glass-soft backdrop-blur transition disabled:cursor-not-allowed disabled:opacity-60 ${
            speech.isListening
              ? "border-rose-300/70 bg-rose-50/80 hover:bg-rose-50"
              : "border-white/70 bg-white/55 hover:-translate-y-0.5 hover:bg-white/70"
          }`}
        >
          <span
            className={`relative grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-white shadow-[0_8px_22px_-12px_rgba(124,92,255,0.55)] ${
              speech.isListening ? "text-rose-500" : "text-iris-indigo"
            }`}
          >
            {speech.isListening ? (
              <>
                <span className="absolute inset-0 animate-ping rounded-2xl bg-rose-300/40" />
                <Mic className="relative h-5 w-5" aria-hidden />
              </>
            ) : speech.isSupported ? (
              <Mic className="h-5 w-5" aria-hidden />
            ) : (
              <MicOff className="h-5 w-5 text-ink-muted" aria-hidden />
            )}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-semibold text-ink sm:text-base">
              {speech.isListening
                ? "Dinleniyor..."
                : "Mikrofonla söylemek istersen"}
            </span>
            <span className="mt-0.5 block text-xs text-ink-muted sm:text-sm">
              {micCardLabel}
            </span>
            {speech.error ? (
              <span className="mt-1 block text-xs font-medium text-rose-600">
                {speech.error}
              </span>
            ) : null}
          </span>
          <ChevronRight className="h-5 w-5 text-ink-muted" aria-hidden />
        </button>

        <div className="mt-6 flex flex-col items-center gap-2">
          <Button
            type="submit"
            variant="gradient"
            size="lg"
            className="min-w-64"
            disabled={loading || !company.trim()}
            title="Ctrl+Enter ile de gönderebilirsin"
          >
            <Sparkles className="h-4 w-4" aria-hidden />
            {loading ? "Anlatılıyor..." : "Anlat"}
          </Button>
          <span className="text-[11px] text-ink-muted">
            <kbd className="rounded border border-slate-200 bg-white/70 px-1 py-0.5 font-mono text-[10px]">Ctrl</kbd>
            {" + "}
            <kbd className="rounded border border-slate-200 bg-white/70 px-1 py-0.5 font-mono text-[10px]">Enter</kbd>
            {" ile hızlı gönder"}
          </span>
        </div>
      </form>

      {favorites.length > 0 ? (
        <div className="mt-10 w-full">
          <div className="flex items-center gap-4 text-xs font-medium uppercase tracking-[0.16em] text-ink-muted">
            <span className="h-px flex-1 bg-slate-200/80 dark:bg-slate-700/60" />
            Favoriler
            <span className="h-px flex-1 bg-slate-200/80 dark:bg-slate-700/60" />
          </div>
          <div className="mt-4 flex flex-wrap justify-center gap-2.5">
            {favorites.map((item) => (
              <div key={item} className="group relative inline-flex">
                <button
                  type="button"
                  onClick={() => onHistoryClick(item)}
                  className="inline-flex h-9 items-center gap-2 rounded-full border border-amber-300/60 bg-amber-50/70 dark:bg-amber-900/20 dark:border-amber-500/30 px-3.5 text-sm font-medium text-ink shadow-glass-soft backdrop-blur transition hover:-translate-y-0.5 hover:bg-amber-50"
                >
                  <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" aria-hidden />
                  {item}
                </button>
                {onFavoriteToggle && (
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onFavoriteToggle(item); }}
                    aria-label="Favoriden çıkar"
                    className="absolute -right-1.5 -top-1.5 hidden h-5 w-5 place-items-center rounded-full bg-white dark:bg-slate-800 shadow text-ink-muted transition hover:text-rose-500 group-hover:grid"
                  >
                    <X className="h-3 w-3" aria-hidden />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {history.length > 0 ? (
        <div className="mt-6 w-full">
          <div className="flex items-center gap-4 text-xs font-medium uppercase tracking-[0.16em] text-ink-muted">
            <span className="h-px flex-1 bg-slate-200/80 dark:bg-slate-700/60" />
            Geçmiş aramalar
            <span className="h-px flex-1 bg-slate-200/80 dark:bg-slate-700/60" />
          </div>
          <div className="mt-4 flex flex-wrap justify-center gap-2.5">
            {history.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onHistoryClick(item)}
                className="inline-flex h-9 items-center gap-2 rounded-full border border-white/70 dark:border-white/10 bg-white/55 dark:bg-white/5 px-3.5 text-sm font-medium text-ink shadow-glass-soft backdrop-blur transition hover:-translate-y-0.5 hover:bg-white/75"
              >
                <Clock className="h-3.5 w-3.5 text-ink-muted" aria-hidden />
                {item}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <GlassCard
        tone="soft"
        className="mt-8 flex w-full items-start gap-4 p-5 text-left"
      >
        <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-iris-indigo" aria-hidden />
        <p className="text-sm leading-6 text-ink-muted">
          Bu uygulama yatırım tavsiyesi vermez. Resmi KAP açıklamalarını anlaşılır
          hale getirir. AI çıktısındaki tavsiye dili otomatik temizlenir.
        </p>
      </GlassCard>
    </section>
  );
}
