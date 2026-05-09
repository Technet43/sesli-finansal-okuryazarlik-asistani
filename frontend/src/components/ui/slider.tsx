"use client";

import * as React from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";
import { cn } from "@/lib/utils";

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(({ className, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn(
      "relative flex w-full touch-none select-none items-center",
      className
    )}
    {...props}
  >
    <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-slate-200/70">
      <SliderPrimitive.Range className="absolute h-full rounded-full bg-iris-gradient" />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb
      aria-label="Değer seçici"
      className="block h-5 w-5 rounded-full border border-white/80 bg-white shadow-[0_8px_22px_-8px_rgba(124,92,255,0.55),inset_0_1px_0_rgba(255,255,255,0.95)] transition-all hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-iris-indigo/60 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
    />
  </SliderPrimitive.Root>
));
Slider.displayName = SliderPrimitive.Root.displayName;

export { Slider };
