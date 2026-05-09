export type ExplanationMode = "simple" | "professional" | "technical";

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
  mode: ExplanationMode;
  useDemo: boolean;
};

export type Notification = {
  date: string;
  title: string;
  plainText: string;
  url?: string;
  category?: string;
};

export type AnomalyFlag = {
  icon: string;
  title: string;
  description: string;
};

export type FinancialNumber = {
  label: string;
  value: string;
};

export type ExplainResponse = {
  company: string;
  summary: string;
  notifications: Notification[];
  anomalies: AnomalyFlag[];
  financialNumbers: FinancialNumber[];
  source: "kap" | "demo" | string;
  disclaimer: string;
};

export type GeminiTestResponse = {
  ok: boolean;
  message: string;
};
