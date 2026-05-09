"use client";

import type { ReactNode } from "react";
import { Loader2, Lock, Moon, ShieldCheck, Sparkles } from "lucide-react";
import type { ExplanationMode, SystemStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { StatusCards } from "./StatusCards";

type SidebarProps = {
  demoMode: boolean;
  setDemoMode: (value: boolean) => void;
  highContrast: boolean;
  setHighContrast: (value: boolean) => void;
  days: number;
  setDays: (value: number) => void;
  summaryCount: number;
  setSummaryCount: (value: number) => void;
  mode: ExplanationMode;
  setMode: (value: ExplanationMode) => void;
  onTestGemini: () => void;
  geminiTesting: boolean;
  geminiMessage: string;
  status: SystemStatus | null;
};

export function Sidebar(props: SidebarProps) {
  return (
    <aside
      aria-label="Ayarlar"
      className="glass-surface flex flex-col gap-7 rounded-2xl p-6 lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold tracking-tight text-ink">Ayarlar</h2>
      </div>

      <div className="space-y-5">
        <ToggleRow
          icon={<Moon className="h-4 w-4 text-ink-muted" aria-hidden />}
          label="Demo modu (offline)"
          description="İnternetsiz örnek bildirimlerle dener."
          checked={props.demoMode}
          onChange={props.setDemoMode}
        />
        <ToggleRow
          icon={<ShieldCheck className="h-4 w-4 text-ink-muted" aria-hidden />}
          label="Yüksek kontrast"
          description="Erişilebilirlik için sade görünüm."
          checked={props.highContrast}
          onChange={props.setHighContrast}
        />
      </div>

      <RangeControl
        label="Kaç günlük KAP bildirimi?"
        value={props.days}
        min={1}
        max={365}
        step={1}
        suffix="gün"
        ticks={[1, 90, 180, 365]}
        onChange={props.setDays}
      />
      <RangeControl
        label="Kaç bildirim özetlensin?"
        value={props.summaryCount}
        min={1}
        max={10}
        step={1}
        ticks={[1, 4, 10]}
        onChange={props.setSummaryCount}
      />

      <div className="space-y-2">
        <span id="mode-label" className="text-sm font-semibold text-ink">
          Anlatım modu
        </span>
        <Select
          value={props.mode}
          onValueChange={(value) => props.setMode(value as ExplanationMode)}
        >
          <SelectTrigger aria-labelledby="mode-label">
            <SelectValue placeholder="Seçim yap" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="simple">Anne-babaya anlatır gibi (sade)</SelectItem>
            <SelectItem value="professional">Kısa profesyonel özet</SelectItem>
            <SelectItem value="technical">Detaylı teknik açıklama</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-3">
        <div className="space-y-1.5">
          <span className="text-sm font-semibold text-ink">Gemini API</span>
          <p className="text-xs leading-5 text-ink-muted">
            Anahtar sunucu tarafında <code className="rounded bg-white/70 px-1 py-0.5 text-[11px] text-ink">.env</code>
            dosyasından okunur. Frontend&apos;e yazılmaz.
          </p>
        </div>
        <div className="flex h-11 items-center gap-2 rounded-xl border border-white/70 bg-white/55 px-3 text-xs text-ink-muted shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]">
          <Lock className="h-4 w-4 text-ink-muted" aria-hidden />
          GEMINI_API_KEY .env üzerinden
        </div>
        <Button
          type="button"
          variant="glass"
          className="w-full justify-center"
          onClick={props.onTestGemini}
          disabled={props.geminiTesting}
        >
          {props.geminiTesting ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <Sparkles className="h-4 w-4 text-iris-indigo" aria-hidden />
          )}
          Gemini bağlantısını test et
        </Button>
        {props.geminiMessage ? (
          <p
            role="status"
            aria-live="polite"
            className="rounded-lg border border-white/60 bg-white/55 px-3 py-2 text-xs leading-5 text-ink-soft"
          >
            {props.geminiMessage}
          </p>
        ) : null}
      </div>

      <StatusCards status={props.status} />
    </aside>
  );
}

function ToggleRow({
  icon,
  label,
  description,
  checked,
  onChange,
}: {
  icon: ReactNode;
  label: string;
  description?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 text-sm">
      <span className="flex items-start gap-3">
        <span className="mt-0.5">{icon}</span>
        <span className="flex flex-col">
          <span className="font-medium text-ink">{label}</span>
          {description ? (
            <span className="text-xs text-ink-muted">{description}</span>
          ) : null}
        </span>
      </span>
      <Switch checked={checked} onCheckedChange={onChange} aria-label={label} />
    </label>
  );
}

function RangeControl({
  label,
  value,
  min,
  max,
  step,
  suffix,
  ticks,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix?: string;
  ticks?: number[];
  onChange: (value: number) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold text-ink">{label}</span>
        <span className="font-mono text-xs font-semibold text-iris-indigo">
          {value}
          {suffix ? ` ${suffix}` : ""}
        </span>
      </div>
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={(values) => onChange(values[0] ?? min)}
        aria-label={label}
      />
      {ticks?.length ? (
        <div className="flex justify-between text-[11px] text-ink-muted">
          {ticks.map((tick) => (
            <span key={tick}>{tick}</span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
