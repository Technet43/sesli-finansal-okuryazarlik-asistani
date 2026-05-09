"use client";

import { MoreVertical, Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Header() {
  return (
    <header className="glass-surface flex items-center justify-between rounded-2xl px-5 py-4 sm:px-6">
      <div className="flex items-center gap-4">
        <div className="relative grid h-12 w-12 place-items-center overflow-hidden rounded-2xl bg-iris-gradient text-xl font-bold text-white shadow-glow">
          <span className="relative">K</span>
          <span className="pointer-events-none absolute inset-x-0 top-0 h-1/2 bg-gradient-to-b from-white/55 to-transparent" />
        </div>
        <div className="flex flex-col">
          <p className="text-lg font-semibold tracking-tight text-ink">KAP Okuryazar</p>
          <p className="text-xs text-ink-muted sm:text-sm">
            KAP bildirimlerini sadeleştirir
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="glass"
          className="hidden sm:inline-flex"
          aria-label="Deploy"
        >
          <Rocket className="h-4 w-4" aria-hidden />
          Deploy
        </Button>
        <Button
          type="button"
          variant="glass"
          size="icon"
          aria-label="Menü"
        >
          <MoreVertical className="h-5 w-5" aria-hidden />
        </Button>
      </div>
    </header>
  );
}
