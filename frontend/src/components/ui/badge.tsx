import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default:
          "border-white/70 bg-white/65 text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.85)] backdrop-blur",
        outline: "border-slate-300/70 bg-transparent text-ink-soft",
        success:
          "border-emerald-200/80 bg-emerald-50/85 text-emerald-700",
        live:
          "border-emerald-200/80 bg-emerald-50/80 text-emerald-700",
        warning:
          "border-amber-200/80 bg-amber-50/85 text-amber-700",
        iris:
          "border-iris-indigo/30 bg-white/70 text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.85),0_8px_22px_-14px_rgba(124,92,255,0.45)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
