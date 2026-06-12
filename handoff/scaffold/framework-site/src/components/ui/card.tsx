import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/*
  Card families from the design system. Grounded separation rules:
    - tonal/inset panels separate by FILL + ROUNDING, not borders
    - floating chat/status cards separate by soft shadow + white fill
    - photographic media cards are high-contrast with no border
  Each is a distinct variant so they never blur together.
*/
const cardVariants = cva("rounded-panel", {
  variants: {
    variant: {
      floating: "bg-surface-primary shadow-card p-6",
      soft: "bg-surface-soft p-8",
      inverse: "bg-surface-inverse text-text-on-inverse p-8",
      media: "bg-surface-media text-text-on-media overflow-hidden",
      outline: "border border-border-hairline bg-surface-primary p-6",
    },
  },
  defaultVariants: { variant: "floating" },
});

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

export function Card({ className, variant, ...props }: CardProps) {
  return <div className={cn(cardVariants({ variant }), className)} {...props} />;
}
