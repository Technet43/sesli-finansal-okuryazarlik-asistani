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
  signal?: AbortSignal
): Promise<ChatResponse> {
  return request<ChatResponse>(
    "/api/chat",
    {
      method: "POST",
      headers: authHeaders(apiKey),
      body: JSON.stringify({ company, context, history, message }),
      externalSignal: signal,
    },
    30_000
  );
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
