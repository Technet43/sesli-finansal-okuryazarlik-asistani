"use client";

import { ChevronRight, Clock, Mic, Search, ShieldCheck, X } from "lucide-react";
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
  onHistoryClick
}: HeroSearchProps) {
  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col items-center text-center">
      <div className="inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/58 px-4 py-2 text-sm font-semibold text-indigo-700 shadow-sm">
        <ShieldCheck className="h-4 w-4" />
        Resmi KAP bildirimleri, sade Türkçe ile
      </div>

      <h1 className="mt-7 max-w-3xl text-balance text-4xl font-semibold tracking-normal text-slate-950 sm:text-5xl lg:text-6xl">
        Hangi şirketin haberlerini anlamak istiyorsun?
      </h1>
      <p className="mt-5 max-w-2xl text-lg text-slate-600">
        Şirket adı yazarak veya sesle sor, gerisini KAP Okuryazar anlatsın.
      </p>

      <div className="mt-8 flex h-16 w-full items-center gap-4 rounded-lg border border-indigo-300/70 bg-white/72 px-5 text-left shadow-glow backdrop-blur">
        <Search className="h-6 w-6 shrink-0 text-slate-500" />
        <input
          aria-label="Şirket adı"
          value={company}
          onChange={(event) => setCompany(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") onSubmit();
          }}
          placeholder="Ziraat Bankası"
          className="min-w-0 flex-1 bg-transparent text-xl font-medium text-slate-950 outline-none placeholder:text-slate-400"
        />
        {company ? (
          <button
            type="button"
            aria-label="Aramayı temizle"
            onClick={() => setCompany("")}
            className="grid h-10 w-10 place-items-center rounded-full bg-slate-100 text-slate-500 transition hover:bg-slate-200"
          >
            <X className="h-5 w-5" />
          </button>
        ) : null}
      </div>

      <button
        type="button"
        className="mt-6 flex w-full max-w-2xl items-center gap-4 rounded-lg border border-white/70 bg-white/58 p-5 text-left shadow-glass transition hover:-translate-y-0.5"
      >
        <span className="grid h-12 w-12 place-items-center rounded-full bg-white text-indigo-600 shadow-sm">
          <Mic className="h-6 w-6" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-semibold text-slate-950">Mikrofonla söylemek istersen</span>
          <span className="mt-1 block text-sm text-slate-600">Sesli sor, KAP Okuryazar anlayıp açıklasın.</span>
        </span>
        <ChevronRight className="h-6 w-6 text-slate-500" />
      </button>

      <button
        type="button"
        onClick={onSubmit}
        disabled={loading || !company.trim()}
        className="mt-6 h-14 min-w-64 rounded-lg bg-gradient-to-r from-sky-500 via-indigo-500 to-fuchsia-500 px-10 text-lg font-semibold text-white shadow-glow transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? "Anlatılıyor..." : "Anlat"}
      </button>

      <div className="mt-8 w-full max-w-4xl">
        <div className="flex items-center gap-4 text-sm text-slate-500">
          <span className="h-px flex-1 bg-slate-200/80" />
          Geçmiş aramalar
          <span className="h-px flex-1 bg-slate-200/80" />
        </div>
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          {history.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => onHistoryClick(item)}
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-white/70 bg-white/58 px-4 text-sm font-semibold text-slate-800 shadow-sm transition hover:-translate-y-0.5"
            >
              <Clock className="h-4 w-4 text-slate-500" />
              {item}
            </button>
          ))}
        </div>
      </div>

      <GlassCard className="mt-8 flex w-full max-w-4xl items-center gap-4 p-5 text-left">
        <ShieldCheck className="h-7 w-7 shrink-0 text-slate-700" />
        <p className="text-sm leading-6 text-slate-600">
          Bu uygulama yatırım tavsiyesi vermez. Resmi KAP açıklamalarını anlaşılır hale getirir.
          AI çıktısındaki tavsiye dili otomatik temizlenir.
        </p>
      </GlassCard>
    </section>
  );
}
