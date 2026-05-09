"use client";

import { MoreVertical, Rocket } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { explainCompany, getStatus, testGemini } from "@/lib/api";
import type { ExplainResponse, SystemStatus } from "@/lib/types";
import { HeroSearch } from "./HeroSearch";
import { ResultsPanel } from "./ResultsPanel";
import { Sidebar } from "./Sidebar";

const DEFAULT_HISTORY = ["Ziraat Bankası", "Koç Holding", "Türk Hava Yolları", "Aselsan", "BİM"];

export function AppShell() {
  const [company, setCompany] = useState("Ziraat Bankası");
  const [days, setDays] = useState(365);
  const [summaryCount, setSummaryCount] = useState(4);
  const [demoMode, setDemoMode] = useState(false);
  const [highContrast, setHighContrast] = useState(false);
  const [mode, setMode] = useState<"simple" | "professional" | "technical">("simple");
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiMessage, setGeminiMessage] = useState("");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [history, setHistory] = useState<string[]>(DEFAULT_HISTORY);
  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem("kap-okuryazar-history");
    if (saved) {
      try {
        setHistory(JSON.parse(saved) as string[]);
      } catch {
        setHistory(DEFAULT_HISTORY);
      }
    }
    void getStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    document.body.classList.toggle("high-contrast", highContrast);
  }, [highContrast]);

  const safeHistory = useMemo(() => history.slice(0, 6), [history]);

  function rememberSearch(value: string) {
    const clean = value.trim();
    if (!clean) return;
    const next = [clean, ...history.filter((item) => item.toLocaleLowerCase("tr") !== clean.toLocaleLowerCase("tr"))].slice(0, 8);
    setHistory(next);
    window.localStorage.setItem("kap-okuryazar-history", JSON.stringify(next));
  }

  async function handleExplain() {
    const clean = company.trim();
    if (!clean) return;
    setLoading(true);
    setError("");
    setResult(null);
    rememberSearch(clean);
    try {
      const response = await explainCompany({
        company: clean,
        days,
        summaryCount,
        mode,
        useDemo: demoMode
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Beklenmeyen bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }

  async function handleTestGemini() {
    setGeminiMessage("Test ediliyor...");
    try {
      const response = await testGemini();
      setGeminiMessage(response.message);
      void getStatus().then(setStatus);
    } catch (err) {
      setGeminiMessage(err instanceof Error ? err.message : "Gemini testi başarısız.");
    }
  }

  return (
    <main className="min-h-screen p-4 text-slate-950 sm:p-6">
      <div className="mx-auto max-w-[1500px] rounded-lg border border-white/70 bg-white/30 p-4 shadow-glass backdrop-blur-2xl">
        <header className="glass-surface flex items-center justify-between rounded-lg px-5 py-4">
          <div className="flex items-center gap-4">
            <div className="grid h-12 w-12 place-items-center rounded-lg bg-gradient-to-br from-sky-500 via-indigo-500 to-fuchsia-500 text-xl font-bold text-white shadow-glow">
              K
            </div>
            <div>
              <p className="text-xl font-semibold text-slate-950">KAP Okuryazar</p>
              <p className="text-sm text-slate-600">KAP bildirimlerini sadeleştirir</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="hidden h-11 items-center gap-2 rounded-lg border border-white/70 bg-white/64 px-4 font-semibold text-slate-900 shadow-sm transition hover:-translate-y-0.5 sm:flex"
            >
              <Rocket className="h-4 w-4" />
              Deploy
            </button>
            <button
              type="button"
              aria-label="Menü"
              className="grid h-11 w-11 place-items-center rounded-lg border border-white/70 bg-white/54 text-slate-800 shadow-sm"
            >
              <MoreVertical className="h-5 w-5" />
            </button>
          </div>
        </header>

        <div className="mt-5 grid gap-5 lg:grid-cols-[320px_1fr]">
          <Sidebar
            demoMode={demoMode}
            setDemoMode={setDemoMode}
            highContrast={highContrast}
            setHighContrast={setHighContrast}
            days={days}
            setDays={setDays}
            summaryCount={summaryCount}
            setSummaryCount={setSummaryCount}
            mode={mode}
            setMode={setMode}
            geminiKey={geminiKey}
            setGeminiKey={setGeminiKey}
            onTestGemini={handleTestGemini}
            geminiMessage={geminiMessage}
            status={status}
          />

          <div className="rounded-lg px-2 py-8 sm:px-6 lg:py-14">
            <HeroSearch
              company={company}
              setCompany={setCompany}
              onSubmit={handleExplain}
              loading={loading}
              history={safeHistory}
              onHistoryClick={(value) => {
                setCompany(value);
              }}
            />
            <ResultsPanel result={result} loading={loading} error={error} />
          </div>
        </div>
      </div>
    </main>
  );
}
