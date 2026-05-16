"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeKatex from "rehype-katex";
import { Bot, Loader2, MessageSquare, Paperclip, RotateCcw, Send, User, X } from "lucide-react";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { streamChat } from "@/lib/api";
import type { ChatMessage, ExplainResponse } from "@/lib/types";
import { GlassCard } from "./GlassCard";

type ChatPanelProps = {
  result: ExplainResponse;
  geminiKey?: string;
  aiConnected?: boolean;
};

type AttachedFile = {
  name: string;
  b64: string;
  mime: string;
  sizeLabel: string;
};

function buildContext(result: ExplainResponse): string {
  const lines: string[] = [`Şirket: ${result.company}`, `Özet: ${result.summary}`];

  // Aggregate key financial values from all notifications so the AI sees them up front.
  const allRows: { date: string; label: string; values: string[] }[] = [];
  for (const n of result.notifications) {
    if (!n.financialTable?.length) continue;
    for (const r of n.financialTable) {
      allRows.push({ date: n.date ?? "", label: r.label, values: r.values });
    }
  }
  if (allRows.length > 0) {
    lines.push("", "=== Anahtar Finansal Değerler (tüm bildirimlerden derlenmiş) ===");
    for (const r of allRows.slice(0, 24)) {
      lines.push(`[${r.date}] ${r.label}: ${r.values.join(" | ")}`);
    }
  }

  lines.push("", "=== Bildirim Detayları ===");
  const limit = Math.min(6, result.notifications.length);
  for (let i = 0; i < limit; i++) {
    const n = result.notifications[i];
    lines.push("", `─── BİLDİRİM ${i + 1} [${n.category ?? ""}] ${n.date ?? ""} ───`);
    lines.push(`Başlık: ${n.title}`);
    if (n.plainText) lines.push(`Özet: ${n.plainText}`);
    if (n.reportText) {
      lines.push(`Rapor verisi: ${n.reportText.slice(0, 4000)}`);
    } else if (n.reportTextError) {
      lines.push("Rapor verisi: Sistem ek içeriği okuyamadı; yalnızca bildirim metnine bakılabilir.");
    }
  }
  return lines.join("\n");
}

const SUGGESTED = [
  "Bu bildirimler yatırımcılar için ne anlama gelir?",
  "PwC denetiminin önemi nedir?",
  "Temettü dağıtımı hakkında ne söylüyor?",
  "Buradaki finans terimleri ne demek?",
  "Neyi dikkatli izlemem gerekir?",
];

const markdownComponents: Components = {
  h2: ({ children }) => <h2 className="mt-3 first:mt-0 text-sm font-semibold text-ink">{children}</h2>,
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
  li: ({ children }) => <li className="pl-1">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
  code: ({ children }) => <code className="rounded bg-ink/5 px-1 py-0.5 text-[0.92em]">{children}</code>,
};

function fileSizeLabel(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function readFileAsB64(file: File): Promise<AttachedFile> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const b64 = dataUrl.split(",")[1] ?? "";
      resolve({ name: file.name, b64, mime: file.type || "application/octet-stream", sizeLabel: fileSizeLabel(file.size) });
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function ChatPanel({ result, geminiKey, aiConnected = false }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [attachment, setAttachment] = useState<AttachedFile | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const context = buildContext(result);

  useEffect(() => {
    setMessages([]);
    setInput("");
    setError("");
    setAttachment(null);
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
      setMessages((prev) => [...prev, userMsg]);
      const historySnapshot = messages;
      const currentAttachment = attachment;
      setAttachment(null);
      setLoading(true);

      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      // Add streaming assistant message
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      try {
        let full = "";
        const gen = streamChat(
          result.company,
          context,
          historySnapshot,
          msg,
          geminiKey,
          ctrl.signal,
          currentAttachment?.b64,
          currentAttachment?.mime,
        );
        for await (const chunk of gen) {
          full += chunk;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: "assistant", content: full };
            return updated;
          });
        }
        if (!full) {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: "assistant", content: "Yanıt alınamadı, tekrar dene." };
            return updated;
          });
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        const msg = err instanceof Error ? err.message : "Bir hata oluştu.";
        setError(msg);
        setMessages((prev) => prev.slice(0, -2)); // remove user + empty assistant
      } finally {
        setLoading(false);
      }
    },
    [input, messages, loading, result.company, context, geminiKey, attachment]
  );

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    try {
      const attached = await readFileAsB64(file);
      setAttachment(attached);
    } catch {
      setError("Dosya okunamadı.");
    }
  }, []);

  const hasAi = aiConnected || !!geminiKey?.trim();

  return (
    <GlassCard className="mx-auto mt-6 w-full max-w-4xl overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/50 dark:border-white/10 px-6 py-4">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-iris-indigo/10 text-iris-indigo">
            <MessageSquare className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold text-ink">{result.company} hakkında sor</p>
            <p className="text-[11px] text-ink-muted">
              {hasAi ? "AI · eğitici finansal Q&A" : "AI API key gerekli · sidebar'dan ekle"}
            </p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => { setMessages([]); setError(""); setAttachment(null); }}
            aria-label="Sohbeti temizle"
            className="grid h-8 w-8 place-items-center rounded-lg bg-white/60 text-ink-muted transition hover:bg-white hover:text-ink"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="max-h-[520px] overflow-y-auto px-6 py-5 space-y-4 scroll-smooth">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-center text-xs text-ink-muted py-2">
              {hasAi
                ? "Bildirimleri anlamak, terimleri öğrenmek veya bağlamını kavramak için sor."
                : "Sohbet özelliği için sidebar'dan AI API key gir."}
            </p>
            {hasAi && (
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
          <div key={i} className={`flex items-start gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${msg.role === "user" ? "bg-iris-indigo text-white" : "bg-white/80 text-iris-indigo shadow-glass-soft"}`}>
              {msg.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </span>
            <div className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 whitespace-pre-wrap ${
              msg.role === "user"
                ? "bg-iris-indigo text-white rounded-tr-sm"
                : "bg-white/70 text-ink shadow-glass-soft rounded-tl-sm"
            }`}>
              {msg.content ? (
                msg.role === "assistant" ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    skipHtml
                    components={markdownComponents}
                  >
                    {msg.content}
                  </ReactMarkdown>
                ) : (
                  msg.content
                )
              ) : (loading && i === messages.length - 1 ? (
                <span className="flex items-center gap-1.5 text-ink-muted">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Yazıyor...</span>
                </span>
              ) : null)}
            </div>
          </div>
        ))}

        {error && <p className="text-center text-xs text-rose-500 py-1">{error}</p>}
        <div ref={bottomRef} />
      </div>

      {/* Attachment preview */}
      {attachment && (
        <div className="mx-6 mb-2 flex items-center gap-2 rounded-xl border border-iris-indigo/30 bg-iris-indigo/5 px-3 py-2 text-xs">
          <Paperclip className="h-3.5 w-3.5 shrink-0 text-iris-indigo" />
          <span className="min-w-0 flex-1 truncate font-medium text-ink">{attachment.name}</span>
          <span className="shrink-0 text-ink-muted">{attachment.sizeLabel}</span>
          <button type="button" onClick={() => setAttachment(null)} aria-label="Dosyayı kaldır" className="shrink-0 text-ink-muted hover:text-rose-500">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-white/50 dark:border-white/10 px-6 py-4">
        <form onSubmit={(e) => { e.preventDefault(); void handleSend(); }} className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.png,.jpg,.jpeg,.webp"
            className="hidden"
            onChange={(e) => void handleFileChange(e)}
          />
          {hasAi && (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Dosya ekle"
              title="PDF, TXT veya görsel ekle"
              className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-white/70 bg-white/60 text-ink-muted shadow-glass-soft transition hover:bg-white hover:text-iris-indigo"
            >
              <Paperclip className="h-4 w-4" />
            </button>
          )}
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={hasAi ? `${result.company} hakkında bir şey sor veya bir kavram sor...` : "AI API key gerekli"}
            disabled={!hasAi || loading}
            className="min-w-0 flex-1 rounded-xl border border-white/70 bg-white/70 px-4 py-2.5 text-sm text-ink outline-none placeholder:text-ink-muted/60 focus:ring-2 focus:ring-iris-indigo/40 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!hasAi || !input.trim() || loading}
            aria-label="Gönder"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-iris-indigo text-white shadow-[0_4px_14px_-4px_rgba(124,92,255,0.6)] transition hover:opacity-90 disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </GlassCard>
  );
}
