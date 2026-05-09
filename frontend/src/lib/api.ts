import type {
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

async function request<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(init?.headers ?? {}),
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

export function getStatus(): Promise<SystemStatus> {
  return request<SystemStatus>("/api/status", { method: "GET" }, 8_000);
}

export function explainCompany(payload: ExplainRequest): Promise<ExplainResponse> {
  return request<ExplainResponse>("/api/explain", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function testGemini(): Promise<GeminiTestResponse> {
  return request<GeminiTestResponse>(
    "/api/test-gemini",
    {
      method: "POST",
      body: JSON.stringify({}),
    },
    20_000
  );
}
