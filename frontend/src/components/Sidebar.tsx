import type { ReactNode } from "react";
import { Lock, Moon, ShieldCheck, Sparkles } from "lucide-react";
import type { SystemStatus } from "@/lib/types";
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
  mode: "simple" | "professional" | "technical";
  setMode: (value: "simple" | "professional" | "technical") => void;
  geminiKey: string;
  setGeminiKey: (value: string) => void;
  onTestGemini: () => void;
  geminiMessage: string;
  status: SystemStatus | null;
};

export function Sidebar(props: SidebarProps) {
  return (
    <aside className="glass-surface rounded-lg p-6 lg:w-[320px]">
      <h2 className="text-base font-semibold text-slate-950">Ayarlar</h2>
      <div className="mt-6 space-y-6">
        <ToggleRow
          icon={<Moon className="h-4 w-4" />}
          label="Demo modu (offline)"
          checked={props.demoMode}
          onChange={props.setDemoMode}
        />
        <ToggleRow
          icon={<ShieldCheck className="h-4 w-4" />}
          label="Yüksek kontrast"
          checked={props.highContrast}
          onChange={props.setHighContrast}
        />

        <RangeControl
          label="Kaç günlük KAP bildirimi?"
          value={props.days}
          min={1}
          max={365}
          suffix="gün"
          onChange={props.setDays}
        />
        <RangeControl
          label="Kaç bildirim özetlensin?"
          value={props.summaryCount}
          min={1}
          max={10}
          onChange={props.setSummaryCount}
        />

        <label className="block space-y-2">
          <span className="text-sm font-semibold text-slate-900">Anlatım modu</span>
          <select
            value={props.mode}
            onChange={(event) => props.setMode(event.target.value as SidebarProps["mode"])}
            className="h-11 w-full rounded-lg border border-slate-200 bg-white/68 px-3 text-sm shadow-inner"
          >
            <option value="simple">Anne-babaya anlatır gibi (sade)</option>
            <option value="professional">Kısa profesyonel özet</option>
            <option value="technical">Detaylı teknik açıklama</option>
          </select>
        </label>

        <div className="space-y-3">
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-slate-900">Gemini API</span>
            <span className="text-xs text-slate-600">Gemini için API key&apos;i buraya gir.</span>
            <span className="flex h-11 items-center gap-2 rounded-lg border border-slate-200 bg-white/68 px-3 shadow-inner">
              <Lock className="h-4 w-4 text-slate-500" />
              <input
                aria-label="Gemini API key"
                type="password"
                value={props.geminiKey}
                onChange={(event) => props.setGeminiKey(event.target.value)}
                placeholder="API key"
                className="min-w-0 flex-1 bg-transparent text-sm outline-none"
              />
            </span>
          </label>
          <button
            type="button"
            onClick={props.onTestGemini}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-lg border border-white/70 bg-white/58 text-sm font-semibold text-indigo-700 shadow-sm transition hover:-translate-y-0.5 hover:shadow-glow"
          >
            <Sparkles className="h-4 w-4" />
            Gemini bağlantısını test et
          </button>
          {props.geminiMessage ? <p className="text-xs text-slate-600">{props.geminiMessage}</p> : null}
        </div>

        <StatusCards status={props.status} />
      </div>
    </aside>
  );
}

function ToggleRow({
  icon,
  label,
  checked,
  onChange
}: {
  icon: ReactNode;
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 text-sm font-medium text-slate-800">
      <span className="flex items-center gap-3">
        {icon}
        {label}
      </span>
      <input
        aria-label={label}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-5 w-9 appearance-none rounded-full bg-slate-300 shadow-inner transition checked:bg-indigo-500 before:block before:h-5 before:w-5 before:rounded-full before:bg-white before:shadow before:transition checked:before:translate-x-4"
      />
    </label>
  );
}

function RangeControl({
  label,
  value,
  min,
  max,
  suffix,
  onChange
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  suffix?: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block space-y-3">
      <span className="flex items-center justify-between text-sm font-semibold text-slate-900">
        {label}
        <span>
          {value} {suffix ?? ""}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full accent-indigo-500"
      />
      <span className="flex justify-between text-xs text-slate-500">
        <span>{min}</span>
        <span>{max}</span>
      </span>
    </label>
  );
}
