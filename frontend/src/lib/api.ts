import type {
  AiProvider,
  ChatMessage,
  ChatResponse,
  ExplainRequest,
  ExplainResponse,
  GeminiTestResponse,
  SystemStatus,
} from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  ""
);
const DEFAULT_TIMEOUT_MS = 60_000;
const ANALYSIS_TIMEOUT_MS = 180_000;
const MAX_AUDIO_BYTES = 5_000_000;

export type AiRequestOptions = {
  provider?: AiProvider;
  geminiKey?: string;
  deepseekKey?: string;
};

function aiHeaders(options?: AiRequestOptions): Record<string, string> {
  const headers: Record<string, string> = {};
  if (options?.provider) headers["X-AI-Provider"] = options.provider;
  const geminiKey = options?.geminiKey?.trim();
  const deepseekKey = options?.deepseekKey?.trim();
  if (geminiKey) headers["X-Gemini-Api-Key"] = geminiKey;
  if (deepseekKey) headers["X-DeepSeek-Api-Key"] = deepseekKey;
  return headers;
}

async function request<T>(
  path: string,
  init?: RequestInit & { externalSignal?: AbortSignal },
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  init?.externalSignal?.addEventListener("abort", () => controller.abort());

  try {
    const { externalSignal: _drop, ...fetchInit } = init ?? {};
    const response = await fetch(`${API_URL}${path}`, {
      ...fetchInit,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(fetchInit?.headers ?? {}),
      },
    });

    if (!response.ok) {
      const payload = (await response
        .json()
        .catch(() => null)) as { detail?: string } | null;
      throw new Error(
        payload?.detail ??
          `Sunucu ${response.status} hatası döndürdü. Lütfen birkaç saniye sonra tekrar dene.`
      );
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Analiz zaman aşımına uğradı. Render free backend, KAP veya AI yavaş cevap veriyor olabilir; lütfen tekrar dene.");
    }
    if (error instanceof TypeError) {
      throw new Error(
        "Backend'e ulaşılamadı. Servis çalışıyor mu? (varsayılan: http://localhost:8000)"
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export function getStatus(options?: AiRequestOptions): Promise<SystemStatus> {
  return request<SystemStatus>(
    "/api/status",
    { method: "GET", headers: aiHeaders(options) },
    8_000
  );
}

export function explainCompany(
  payload: ExplainRequest,
  options?: AiRequestOptions,
  signal?: AbortSignal
): Promise<ExplainResponse> {
  return request<ExplainResponse>(
    "/api/explain",
    {
      method: "POST",
      headers: aiHeaders(options),
      body: JSON.stringify(payload),
      externalSignal: signal,
    },
    ANALYSIS_TIMEOUT_MS
  );
}

export function testGemini(options?: AiRequestOptions): Promise<GeminiTestResponse> {
  return request<GeminiTestResponse>(
    "/api/test-gemini",
    {
      method: "POST",
      headers: aiHeaders(options),
      body: JSON.stringify({}),
    },
    20_000
  );
}

export function sendChat(
  company: string,
  context: string,
  history: ChatMessage[],
  message: string,
  options?: AiRequestOptions,
  signal?: AbortSignal,
  fileB64?: string,
  fileMime?: string,
): Promise<ChatResponse> {
  return request<ChatResponse>(
    "/api/chat",
    {
      method: "POST",
      headers: aiHeaders(options),
      body: JSON.stringify({ company, context, history, message, file_b64: fileB64 ?? null, file_mime: fileMime ?? null }),
      externalSignal: signal,
    },
    30_000
  );
}

export async function* streamChat(
  company: string,
  context: string,
  history: ChatMessage[],
  message: string,
  options?: AiRequestOptions,
  signal?: AbortSignal,
  fileB64?: string,
  fileMime?: string,
): AsyncGenerator<string> {
  const response = await fetch(`${API_URL}/api/chat/stream`, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...aiHeaders(options),
    },
    body: JSON.stringify({ company, context, history, message, file_b64: fileB64 ?? null, file_mime: fileMime ?? null }),
  });
  if (!response.ok) {
    const err = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(err?.detail ?? `HTTP ${response.status}`);
  }
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      if (!part.startsWith("data: ")) continue;
      const data = part.slice(6).trim();
      if (data === "[DONE]") return;
      try {
        const parsed = JSON.parse(data) as { text?: string; error?: string };
        if (parsed.error) throw new Error(parsed.error);
        if (parsed.text) yield parsed.text;
      } catch { /* ignore malformed */ }
    }
  }
}

export async function transcribeAudio(audioBlob: Blob, apiKey?: string): Promise<string> {
  if (audioBlob.size > MAX_AUDIO_BYTES) {
    throw new Error("Ses kaydı çok uzun. Lütfen daha kısa bir kayıt dene.");
  }
  const buffer = await audioBlob.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  const audio_b64 = btoa(binary);
  const mime_type = audioBlob.type || "audio/webm";
  const res = await request<{ text: string }>(
    "/api/transcribe/audio",
    {
      method: "POST",
      headers: aiHeaders({ geminiKey: apiKey }),
      body: JSON.stringify({ audio_b64, mime_type }),
    },
    25_000
  );
  return res.text;
}

export async function fetchTTS(text: string, apiKey?: string, voice = "Aoede"): Promise<ArrayBuffer> {
  const res = await request<{ audio_b64: string; format: string }>(
    "/api/tts",
    {
      method: "POST",
      headers: aiHeaders({ geminiKey: apiKey }),
      body: JSON.stringify({ text, voice }),
    },
    30_000
  );
  const binary = atob(res.audio_b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}
