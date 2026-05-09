import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-all duration-200 will-change-transform focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-iris-indigo/60 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-55",
  {
    variants: {
      variant: {
        default:
          "bg-ink text-white shadow-[0_8px_24px_-12px_rgba(15,23,42,0.45)] hover:bg-ink-soft",
        glass:
          "border border-white/70 bg-white/65 text-ink shadow-glass-soft backdrop-blur hover:-translate-y-0.5 hover:bg-white/80",
        gradient:
          "relative overflow-hidden bg-iris-gradient text-white shadow-glow hover:-translate-y-0.5 hover:shadow-[0_0_0_1px_rgba(124,92,255,0.3),0_30px_70px_-20px_rgba(124,92,255,0.55)]",
        ghost:
          "text-ink hover:bg-white/60 hover:backdrop-blur",
        outline:
          "border border-slate-300/80 bg-transparent text-ink hover:bg-white/60",
      },
      size: {
        default: "h-11 px-5",
        sm: "h-9 px-3 text-xs",
        lg: "h-14 px-9 text-base",
        icon: "h-11 w-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
