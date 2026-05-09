"use client";

import { useEffect, useMemo, useState } from "react";
import { explainCompany, getStatus, testGemini } from "@/lib/api";
import type { ExplainResponse, ExplanationMode, SystemStatus } from "@/lib/types";
import { Header } from "./Header";
import { HeroSearch } from "./HeroSearch";
import { ResultsPanel } from "./ResultsPanel";
import { Sidebar } from "./Sidebar";

const DEFAULT_HISTORY = [
  "Ziraat Bankası",
  "Koç Holding",
  "Türk Hava Yolları",
  "Aselsan",
  "BİM",
];
const HISTORY_KEY = "kap-okuryazar-history";
const GEMINI_KEY_STORAGE = "kap-okuryazar-gemini-key";
const HISTORY_LIMIT = 8;

export function AppShell() {
  const [company, setCompany] = useState("Ziraat Bankası");
  const [days, setDays] = useState(365);
  const [summaryCount, setSummaryCount] = useState(4);
  const [demoMode, setDemoMode] = useState(false);
  const [highContrast, setHighContrast] = useState(false);
  const [mode, setMode] = useState<ExplanationMode>("simple");
  const [geminiKey, setGeminiKeyState] = useState("");
  const [geminiTesting, setGeminiTesting] = useState(false);
  const [geminiMessage, setGeminiMessage] = useState("");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [history, setHistory] = useState<string[]>(DEFAULT_HISTORY);
  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function setGeminiKey(value: string) {
    setGeminiKeyState(value);
    try {
      if (value) {
        window.sessionStorage.setItem(GEMINI_KEY_STORAGE, value);
      } else {
        window.sessionStorage.removeItem(GEMINI_KEY_STORAGE);
      }
    } catch {
      // ignore storage errors
    }
  }

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(HISTORY_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as string[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setHistory(parsed);
        }
      }
    } catch {
      setHistory(DEFAULT_HISTORY);
    }
    try {
      const savedKey = window.sessionStorage.getItem(GEMINI_KEY_STORAGE);
      if (savedKey) {
        setGeminiKeyState(savedKey);
      }
    } catch {
      // ignore
    }
    void getStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    document.body.classList.toggle("high-contrast", highContrast);
  }, [highContrast]);

  const safeHistory = useMemo(() => history.slice(0, 6), [history]);

  function rememberSearch(value: string) {
    const clean = value.trim();
    if (!clean) return;
    const next = [
      clean,
      ...history.filter(
        (item) => item.toLocaleLowerCase("tr") !== clean.toLocaleLowerCase("tr")
      ),
    ].slice(0, HISTORY_LIMIT);
    setHistory(next);
    try {
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
    } catch {
      // ignore quota / private mode errors
    }
  }

  async function handleExplain() {
    const clean = company.trim();
    if (!clean) return;
    setLoading(true);
    setError("");
    setResult(null);
    rememberSearch(clean);
    try {
      const response = await explainCompany(
        {
          company: clean,
          days,
          summaryCount,
          mode,
          useDemo: demoMode,
        },
        geminiKey
      );
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Beklenmeyen bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }

  async function handleTestGemini() {
    setGeminiTesting(true);
    setGeminiMessage("Test ediliyor...");
    try {
      const response = await testGemini(geminiKey);
      setGeminiMessage(response.message);
      void getStatus(geminiKey)
        .then(setStatus)
        .catch(() => undefined);
    } catch (err) {
      setGeminiMessage(err instanceof Error ? err.message : "Gemini testi başarısız.");
    } finally {
      setGeminiTesting(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-6">
        <Header />

        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
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
            geminiTesting={geminiTesting}
            geminiMessage={geminiMessage}
            status={status}
          />

          <div className="px-1 pb-12 pt-4 sm:px-4 lg:py-10">
            <HeroSearch
              company={company}
              setCompany={setCompany}
              onSubmit={handleExplain}
              loading={loading}
              history={safeHistory}
              onHistoryClick={(value) => setCompany(value)}
            />
            <ResultsPanel result={result} loading={loading} error={error} />
          </div>
        </div>
      </div>
    </main>
  );
}
