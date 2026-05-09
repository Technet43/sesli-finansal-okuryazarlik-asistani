import type { ExplainRequest, ExplainResponse, GeminiTestResponse, SystemStatus } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `API hatası: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getStatus(): Promise<SystemStatus> {
  return request<SystemStatus>("/api/status");
}

export function explainCompany(payload: ExplainRequest): Promise<ExplainResponse> {
  return request<ExplainResponse>("/api/explain", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function testGemini(): Promise<GeminiTestResponse> {
  return request<GeminiTestResponse>("/api/test-gemini", {
    method: "POST",
    body: JSON.stringify({})
  });
}
