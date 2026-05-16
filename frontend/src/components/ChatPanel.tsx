"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, Loader2, MessageSquare, RotateCcw, Send, User } from "lucide-react";
import { sendChat } from "@/lib/api";
import type { ChatMessage, ExplainResponse } from "@/lib/types";
import { GlassCard } from "./GlassCard";

type ChatPanelProps = {
  result: ExplainResponse;
  geminiKey?: string;
};

function buildContext(result: ExplainResponse): string {
  const lines: string[] = [`Şirket: ${result.company}`, `Özet: ${result.summary}`, ""];
  for (const n of result.notifications.slice(0, 8)) {
    lines.push(`[${n.date ?? ""}] ${n.title}`);
    if (n.plainText) lines.push(n.plainText);
  }
  return lines.join("\n");
}

const SUGGESTED = [
  "Son bildirimlerde dikkat çeken bir şey var mı?",
  "Temettü dağıtımı hakkında ne söylüyor?",
  "Finansal sonuçlar nasıl yorumlanabilir?",
  "Yönetim değişikliği var mı?",
];

export function ChatPanel({ result, geminiKey }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const context = buildContext(result);

  // Reset chat when company changes
  useEffect(() => {
    setMessages([]);
    setInput("");
    setError("");
    abortRef.current?.abort();
  }, [result.company]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(
    async (text?: string) => {
      const msg = (text ?? input).trim();
      if (!msg || loading) return;
      setInput("");
      setError("");

      const userMsg: ChatMessage = { role: "user", content: msg };
      const nextHistory = [...messages, userMsg];
      setMessages(nextHistory);
      setLoading(true);

      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      try {
        const res = await sendChat(result.company, context, messages, msg, geminiKey, ctrl.signal);
        setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Bir hata oluştu.");
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setLoading(false);
      }
    },
    [input, messages, loading, result.company, context, geminiKey]
  );

  const hasGemini = !!geminiKey?.trim();

  return (
    <GlassCard className="mx-auto mt-6 w-full max-w-4xl overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/50 px-6 py-4">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-iris-indigo/10 text-iris-indigo">
            <MessageSquare className="h-4 w-4" aria-hidden />
          </span>
          <div>
            <p className="text-sm font-semibold text-ink">{result.company} hakkında sor</p>
            <p className="text-[11px] text-ink-muted">
              {hasGemini ? "Gemini AI" : "Gemini API key gerekli"} · bildirimler üzerinden Q&A
            </p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => { setMessages([]); setError(""); }}
            aria-label="Sohbeti temizle"
            className="grid h-8 w-8 place-items-center rounded-lg bg-white/60 text-ink-muted transition hover:bg-white hover:text-ink"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden />
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="max-h-[480px] overflow-y-auto px-6 py-5 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-center text-xs text-ink-muted py-2">
              {hasGemini
                ? "Bildirimler hakkında istediğinizi sorun — bağlam otomatik aktarılır."
                : "Sohbet özelliği için sidebar'dan Gemini API key gir."}
            </p>
            {hasGemini && (
              <div className="flex flex-wrap gap-2 justify-center">
                {SUGGESTED.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => void handleSend(s)}
                    className="rounded-full border border-white/70 bg-white/60 px-3 py-1.5 text-xs font-medium text-ink-soft shadow-glass-soft transition hover:-translate-y-0.5 hover:bg-white/80"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex items-start gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${msg.role === "user" ? "bg-iris-indigo text-white" : "bg-white text-iris-indigo shadow-glass-soft"}`}>
              {msg.role === "user"
                ? <User className="h-4 w-4" aria-hidden />
                : <Bot className="h-4 w-4" aria-hidden />}
            </span>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                msg.role === "user"
                  ? "bg-iris-indigo text-white rounded-tr-sm"
                  : "bg-white/70 text-ink shadow-glass-soft rounded-tl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-start gap-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white text-iris-indigo shadow-glass-soft">
              <Bot className="h-4 w-4" aria-hidden />
            </span>
            <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-white/70 px-4 py-3 shadow-glass-soft">
              <Loader2 className="h-4 w-4 animate-spin text-iris-indigo" aria-hidden />
              <span className="text-sm text-ink-muted">Yanıt hazırlanıyor...</span>
            </div>
          </div>
        )}

        {error && (
          <p className="text-center text-xs text-rose-500">{error}</p>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-white/50 px-6 py-4">
        <form
          onSubmit={(e) => { e.preventDefault(); void handleSend(); }}
          className="flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={hasGemini ? `${result.company} hakkında sor...` : "Gemini API key gerekli"}
            disabled={!hasGemini || loading}
            className="min-w-0 flex-1 rounded-xl border border-white/70 bg-white/70 px-4 py-2.5 text-sm text-ink outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-iris-indigo/40 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!hasGemini || !input.trim() || loading}
            aria-label="Gönder"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-iris-indigo text-white shadow-[0_4px_14px_-4px_rgba(124,92,255,0.6)] transition hover:opacity-90 disabled:opacity-40"
          >
            {loading
              ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              : <Send className="h-4 w-4" aria-hidden />}
          </button>
        </form>
      </div>
    </GlassCard>
  );
}
