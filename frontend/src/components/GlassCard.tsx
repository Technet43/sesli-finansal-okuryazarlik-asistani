import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

type GlassCardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  tone?: "default" | "soft";
};

export function GlassCard({
  children,
  className,
  tone = "default",
  ...props
}: GlassCardProps) {
  return (
    <div
      className={cn(
        tone === "soft" ? "glass-soft" : "glass-surface",
        "rounded-2xl",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
