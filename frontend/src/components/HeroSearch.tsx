"use client";

import {
  ChevronRight,
  Clock,
  Mic,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "./GlassCard";

type HeroSearchProps = {
  company: string;
  setCompany: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  history: string[];
  onHistoryClick: (value: string) => void;
};

export function HeroSearch({
  company,
  setCompany,
  onSubmit,
  loading,
  history,
  onHistoryClick,
}: HeroSearchProps) {
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
          aria-label="Mikrofonla söyle (yakında)"
          title="Mikrofon desteği yakında"
          className="mt-5 flex w-full items-center gap-4 rounded-2xl border border-white/70 bg-white/55 p-4 text-left shadow-glass-soft backdrop-blur transition hover:-translate-y-0.5 hover:bg-white/70"
        >
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-white text-iris-indigo shadow-[0_8px_22px_-12px_rgba(124,92,255,0.55)]">
            <Mic className="h-5 w-5" aria-hidden />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-semibold text-ink sm:text-base">
              Mikrofonla söylemek istersen
            </span>
            <span className="mt-0.5 block text-xs text-ink-muted sm:text-sm">
              Sesli sor, KAP Okuryazar anlayıp açıklasın.
            </span>
          </span>
          <ChevronRight className="h-5 w-5 text-ink-muted" aria-hidden />
        </button>

        <div className="mt-6 flex justify-center">
          <Button
            type="submit"
            variant="gradient"
            size="lg"
            className="min-w-64"
            disabled={loading || !company.trim()}
          >
            <Sparkles className="h-4 w-4" aria-hidden />
            {loading ? "Anlatılıyor..." : "Anlat"}
          </Button>
        </div>
      </form>

      {history.length > 0 ? (
        <div className="mt-10 w-full">
          <div className="flex items-center gap-4 text-xs font-medium uppercase tracking-[0.16em] text-ink-muted">
            <span className="h-px flex-1 bg-slate-200/80" />
            Geçmiş aramalar
            <span className="h-px flex-1 bg-slate-200/80" />
          </div>
          <div className="mt-4 flex flex-wrap justify-center gap-2.5">
            {history.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onHistoryClick(item)}
                className="inline-flex h-9 items-center gap-2 rounded-full border border-white/70 bg-white/55 px-3.5 text-sm font-medium text-ink shadow-glass-soft backdrop-blur transition hover:-translate-y-0.5 hover:bg-white/75"
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
