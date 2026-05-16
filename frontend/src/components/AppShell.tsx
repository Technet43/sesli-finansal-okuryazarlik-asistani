"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GitCompareArrows } from "lucide-react";
import { explainCompany, getStatus, testGemini } from "@/lib/api";
import type { ExplainResponse, ExplanationMode, SystemStatus } from "@/lib/types";
import { Header } from "./Header";
import { HeroSearch } from "./HeroSearch";
import { ResultsPanel } from "./ResultsPanel";
import { ComparisonPanel } from "./ComparisonPanel";
import { ChatPanel } from "./ChatPanel";
import { Sidebar } from "./Sidebar";

const DEFAULT_HISTORY = [
  "Ziraat Bankası",
  "Koç Holding",
  "Türk Hava Yolları",
  "Aselsan",
  "BİM",
];
const HISTORY_KEY = "kap-okuryazar-history";
const FAVORITES_KEY = "kap-okuryazar-favorites";
const GEMINI_KEY_STORAGE = "kap-okuryazar-gemini-key";
const HISTORY_LIMIT = 8;
const FAVORITES_LIMIT = 12;
const STATUS_CACHE_TTL_MS = 30_000;

export function AppShell() {
  const [company, setCompany] = useState("Ziraat Bankası");
  const [companyB, setCompanyB] = useState("");
  const [compareMode, setCompareMode] = useState(false);
  const [days, setDays] = useState(365);
  const [summaryCount, setSummaryCount] = useState(4);
  const [demoMode, setDemoMode] = useState(false);
  const [darkMode, setDarkModeState] = useState(false);
  const [highContrast, setHighContrast] = useState(false);
  const [mode, setMode] = useState<ExplanationMode>("professional");
  const [ttsRate, setTtsRateState] = useState(0.92);
  const [geminiKey, setGeminiKeyState] = useState("");
  const [geminiTesting, setGeminiTesting] = useState(false);
  const [geminiMessage, setGeminiMessage] = useState("");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [history, setHistory] = useState<string[]>(DEFAULT_HISTORY);
  const [favorites, setFavoritesState] = useState<string[]>([]);
  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [resultB, setResultB] = useState<ExplainResponse | null>(null);
  const [error, setError] = useState("");
  const [errorB, setErrorB] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingB, setLoadingB] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const abortRefB = useRef<AbortController | null>(null);
  const statusCacheRef = useRef<{ data: SystemStatus; ts: number } | null>(null);

  function setDarkMode(value: boolean) {
    setDarkModeState(value);
    try { window.localStorage.setItem("kap-okuryazar-dark", value ? "1" : "0"); } catch { /* ignore */ }
  }

  function setTtsRate(value: number) {
    setTtsRateState(value);
    try { window.localStorage.setItem("kap-okuryazar-tts-rate", String(value)); } catch { /* ignore */ }
  }

  function setGeminiKey(value: string) {
    setGeminiKeyState(value);
    try {
      if (value) window.sessionStorage.setItem(GEMINI_KEY_STORAGE, value);
      else window.sessionStorage.removeItem(GEMINI_KEY_STORAGE);
    } catch { /* ignore */ }
  }

  async function refreshStatus(apiKey?: string) {
    const now = Date.now();
    if (!apiKey && statusCacheRef.current && now - statusCacheRef.current.ts < STATUS_CACHE_TTL_MS) {
      setStatus(statusCacheRef.current.data);
      return;
    }
    try {
      const data = await getStatus(apiKey);
      setStatus(data);
      if (!apiKey) statusCacheRef.current = { data, ts: now };
    } catch {
      setStatus(null);
    }
  }

  useEffect(() => {
    try {
      const savedDark = window.localStorage.getItem("kap-okuryazar-dark");
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      const isDark = savedDark !== null ? savedDark === "1" : prefersDark;
      setDarkModeState(isDark);
      document.documentElement.classList.toggle("dark", isDark);
    } catch { /* ignore */ }
    try {
      const savedRate = window.localStorage.getItem("kap-okuryazar-tts-rate");
      if (savedRate) {
        const parsed = parseFloat(savedRate);
        if (!isNaN(parsed) && parsed >= 0.5 && parsed <= 1.8) setTtsRateState(parsed);
      }
    } catch { /* ignore */ }
    try {
      const savedFavs = window.localStorage.getItem(FAVORITES_KEY);
      if (savedFavs) {
        const parsed = JSON.parse(savedFavs) as string[];
        if (Array.isArray(parsed)) setFavoritesState(parsed);
      }
    } catch { /* ignore */ }
    try {
      const saved = window.localStorage.getItem(HISTORY_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as string[];
        if (Array.isArray(parsed) && parsed.length > 0) setHistory(parsed);
      }
    } catch { setHistory(DEFAULT_HISTORY); }
    try {
      const savedKey = window.sessionStorage.getItem(GEMINI_KEY_STORAGE);
      if (savedKey) setGeminiKeyState(savedKey);
    } catch { /* ignore */ }
    void refreshStatus();
  }, []);

  useEffect(() => { document.body.classList.toggle("high-contrast", highContrast); }, [highContrast]);
  useEffect(() => { document.documentElement.classList.toggle("dark", darkMode); }, [darkMode]);
  useEffect(() => {
    if (compareMode && result && resultB) {
      document.title = `${result.company} vs ${resultB.company} — KAP Okuryazar`;
    } else if (result) {
      document.title = `${result.company} — KAP Okuryazar`;
    } else {
      document.title = "KAP Okuryazar";
    }
  }, [result, resultB, compareMode]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !loading) {
        event.preventDefault();
        void handleExplainWith();
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [loading, company, days, summaryCount, mode, demoMode, geminiKey]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const safeHistory = useMemo(() => history.slice(0, 6), [history]);

  function toggleFavorite(value: string) {
    const clean = value.trim();
    if (!clean) return;
    setFavoritesState((prev) => {
      const exists = prev.some((f) => f.toLocaleLowerCase("tr") === clean.toLocaleLowerCase("tr"));
      const next = exists
        ? prev.filter((f) => f.toLocaleLowerCase("tr") !== clean.toLocaleLowerCase("tr"))
        : [clean, ...prev].slice(0, FAVORITES_LIMIT);
      try { window.localStorage.setItem(FAVORITES_KEY, JSON.stringify(next)); } catch { /* ignore */ }
      return next;
    });
  }

  function rememberSearch(value: string) {
    const clean = value.trim();
    if (!clean) return;
    const next = [
      clean,
      ...history.filter((item) => item.toLocaleLowerCase("tr") !== clean.toLocaleLowerCase("tr")),
    ].slice(0, HISTORY_LIMIT);
    setHistory(next);
    try { window.localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); } catch { /* ignore */ }
  }

  async function fetchFor(
    companyName: string,
    abortCtrl: React.MutableRefObject<AbortController | null>,
    setRes: (r: ExplainResponse | null) => void,
    setErr: (e: string) => void,
    setLoad: (b: boolean) => void,
    notify: boolean
  ) {
    const clean = companyName.trim();
    if (!clean) return;
    abortCtrl.current?.abort();
    const controller = new AbortController();
    abortCtrl.current = controller;
    setLoad(true);
    setErr("");
    setRes(null);
    rememberSearch(clean);
    try {
      const response = await explainCompany(
        { company: clean, days, summaryCount, mode, useDemo: demoMode },
        geminiKey,
        controller.signal
      );
      setRes(response);
      if (notify && document.hidden && "Notification" in window && Notification.permission === "granted") {
        new Notification("KAP Okuryazar", { body: `${response.company} analizi hazır.`, icon: "/favicon.ico" });
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setErr(err instanceof Error ? err.message : "Beklenmeyen bir hata oluştu.");
    } finally {
      setLoad(false);
    }
  }

  async function handleExplainWith(companyOverride?: string) {
    const clean = (companyOverride ?? company).trim();
    if (!clean) return;

    if ("Notification" in window && Notification.permission === "default") {
      void Notification.requestPermission();
    }

    if (compareMode) {
      const cleanB = companyB.trim();
      await Promise.all([
        fetchFor(clean, abortRef, setResult, setError, setLoading, true),
        cleanB ? fetchFor(cleanB, abortRefB, setResultB, setErrorB, setLoadingB, false) : Promise.resolve(),
      ]);
    } else {
      await fetchFor(clean, abortRef, setResult, setError, setLoading, true);
    }
  }

  function handleExplain() { void handleExplainWith(); }

  function handleHistoryClick(value: string) {
    setCompany(value);
    void handleExplainWith(value);
  }

  async function handleTestGemini() {
    setGeminiTesting(true);
    setGeminiMessage("Test ediliyor...");
    try {
      const response = await testGemini(geminiKey);
      setGeminiMessage(response.message);
      void refreshStatus(geminiKey);
    } catch (err) {
      setGeminiMessage(err instanceof Error ? err.message : "Gemini testi başarısız.");
    } finally {
      setGeminiTesting(false);
    }
  }

  function toggleCompareMode() {
    setCompareMode((prev) => {
      if (prev) {
        setResultB(null);
        setErrorB("");
        setCompanyB("");
      }
      return !prev;
    });
  }

  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-6">
        <Header />

        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <Sidebar
            demoMode={demoMode}
            setDemoMode={setDemoMode}
            darkMode={darkMode}
            setDarkMode={setDarkMode}
            highContrast={highContrast}
            setHighContrast={setHighContrast}
            days={days}
            setDays={setDays}
            summaryCount={summaryCount}
            setSummaryCount={setSummaryCount}
            mode={mode}
            setMode={setMode}
            ttsRate={ttsRate}
            setTtsRate={setTtsRate}
            geminiKey={geminiKey}
            setGeminiKey={setGeminiKey}
            onTestGemini={handleTestGemini}
            geminiTesting={geminiTesting}
            geminiMessage={geminiMessage}
            status={status}
          />

          <div className="px-1 pb-12 pt-4 sm:px-4 lg:py-10">
            <div className="flex items-start gap-4">
              <div className="flex-1">
                <HeroSearch
                  company={company}
                  setCompany={setCompany}
                  onSubmit={handleExplain}
                  loading={loading}
                  history={safeHistory}
                  onHistoryClick={handleHistoryClick}
                  favorites={favorites}
                  onFavoriteToggle={toggleFavorite}
                />
              </div>
              <button
                type="button"
                onClick={toggleCompareMode}
                title={compareMode ? "Karşılaştırma modunu kapat" : "İki şirketi karşılaştır"}
                aria-pressed={compareMode}
                className={`mt-[88px] flex h-10 items-center gap-2 rounded-xl border px-3 text-sm font-medium shadow-glass-soft backdrop-blur transition hover:-translate-y-0.5 ${
                  compareMode
                    ? "border-iris-indigo/40 bg-iris-indigo/10 text-iris-indigo"
                    : "border-white/70 bg-white/55 text-ink-muted hover:bg-white/75"
                }`}
              >
                <GitCompareArrows className="h-4 w-4" aria-hidden />
                <span className="hidden sm:inline">{compareMode ? "Karşılaştır" : "Karşılaştır"}</span>
              </button>
            </div>

            {compareMode && (
              <div className="mt-4 animate-fade-in">
                <label className="block mb-1.5 text-xs font-semibold text-ink-muted uppercase tracking-wider">
                  Karşılaştırılacak 2. Şirket
                </label>
                <div className="flex h-[52px] items-center gap-3 rounded-xl border border-white/70 bg-white/72 px-4 shadow-glass backdrop-blur-xl">
                  <GitCompareArrows className="h-4 w-4 shrink-0 text-iris-indigo" aria-hidden />
                  <input
                    type="text"
                    value={companyB}
                    onChange={(e) => setCompanyB(e.target.value)}
                    placeholder="Örn: Türk Hava Yolları"
                    autoComplete="off"
                    className="min-w-0 flex-1 bg-transparent text-base font-medium text-ink outline-none placeholder:text-slate-400"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") { e.preventDefault(); handleExplain(); }
                    }}
                  />
                  {companyB && (
                    <button
                      type="button"
                      onClick={() => setCompanyB("")}
                      className="text-ink-muted transition hover:text-ink"
                      aria-label="Temizle"
                    >
                      ×
                    </button>
                  )}
                </div>
              </div>
            )}

            {compareMode ? (
              <ComparisonPanel
                resultA={result}
                resultB={resultB}
                loadingA={loading}
                loadingB={loadingB}
                errorA={error}
                errorB={errorB}
                onRetryA={handleExplain}
                onRetryB={() => {
                  if (companyB.trim()) {
                    void fetchFor(companyB, abortRefB, setResultB, setErrorB, setLoadingB, false);
                  }
                }}
                ttsRate={ttsRate}
                geminiKey={geminiKey}
              />
            ) : (
              <>
                <ResultsPanel
                  result={result}
                  loading={loading}
                  error={error}
                  onRetry={handleExplain}
                  ttsRate={ttsRate}
                  geminiKey={geminiKey}
                  isFavorite={result ? favorites.some((f) => f.toLocaleLowerCase("tr") === result.company.toLocaleLowerCase("tr")) : false}
                  onFavoriteToggle={() => result && toggleFavorite(result.company)}
                />
                {result && !loading && (
                  <ChatPanel result={result} geminiKey={geminiKey} />
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
