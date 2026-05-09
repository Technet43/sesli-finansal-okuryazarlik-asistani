export type SystemStatus = {
  kap: {
    status: "live" | "fallback" | "offline" | string;
    label: string;
  };
  gemini: {
    status: "connected" | "fallback" | "offline" | string;
    label: string;
  };
  lastCheck: string;
};

export type ExplainRequest = {
  company: string;
  days: number;
  summaryCount: number;
  mode: "simple" | "professional" | "technical";
  useDemo: boolean;
};

export type Notification = {
  date: string;
  title: string;
  plainText: string;
};

export type ExplainResponse = {
  company: string;
  summary: string;
  notifications: Notification[];
  source: "kap" | "demo" | string;
  disclaimer: string;
};

export type GeminiTestResponse = {
  ok: boolean;
  message: string;
};
