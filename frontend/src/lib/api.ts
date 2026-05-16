import type {
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

function authHeaders(apiKey?: string): Record<string, string> {
  const key = apiKey?.trim();
  return key ? { "X-Gemini-Api-Key": key } : {};
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
      throw new Error("İstek zaman aşımına uğradı. Backend yavaş cevap veriyor olabilir.");
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

export function getStatus(apiKey?: string): Promise<SystemStatus> {
  return request<SystemStatus>(
    "/api/status",
    { method: "GET", headers: authHeaders(apiKey) },
    8_000
  );
}

export function explainCompany(
  payload: ExplainRequest,
  apiKey?: string,
  signal?: AbortSignal
): Promise<ExplainResponse> {
  return request<ExplainResponse>("/api/explain", {
    method: "POST",
    headers: authHeaders(apiKey),
    body: JSON.stringify(payload),
    externalSignal: signal,
  });
}

export function testGemini(apiKey?: string): Promise<GeminiTestResponse> {
  return request<GeminiTestResponse>(
    "/api/test-gemini",
    {
      method: "POST",
      headers: authHeaders(apiKey),
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
  apiKey?: string,
  signal?: AbortSignal,
  fileB64?: string,
  fileMime?: string,
): Promise<ChatResponse> {
  return request<ChatResponse>(
    "/api/chat",
    {
      method: "POST",
      headers: authHeaders(apiKey),
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
  apiKey?: string,
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
      ...authHeaders(apiKey),
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
      headers: authHeaders(apiKey),
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
      headers: authHeaders(apiKey),
      body: JSON.stringify({ text, voice }),
    },
    30_000
  );
  const binary = atob(res.audio_b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}
