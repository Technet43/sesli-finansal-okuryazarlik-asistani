"use client";

import * as React from "react";
import * as SwitchPrimitives from "@radix-ui/react-switch";
import { cn } from "@/lib/utils";

const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitives.Root
    ref={ref}
    className={cn(
      "peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-white/70 bg-slate-200/80 shadow-inner transition-colors duration-200",
      "data-[state=checked]:bg-iris-indigo data-[state=checked]:shadow-[0_0_0_1px_rgba(124,92,255,0.45),0_8px_24px_-12px_rgba(124,92,255,0.55)]",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-iris-indigo/60 focus-visible:ring-offset-2",
      "disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    {...props}
  >
    <SwitchPrimitives.Thumb
      className={cn(
        "pointer-events-none block h-5 w-5 translate-x-0.5 rounded-full bg-white shadow-md ring-0 transition-transform duration-200",
        "data-[state=checked]:translate-x-[1.375rem]"
      )}
    />
  </SwitchPrimitives.Root>
));
Switch.displayName = SwitchPrimitives.Root.displayName;

export { Switch };
