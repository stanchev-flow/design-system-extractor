import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/*
  typography.eyebrow — small tracked uppercase label inside a low-contrast tonal
  pill. textTransform:uppercase is implemented in CSS (rule: don't rely on copy
  being typed uppercase).
*/
const badgeVariants = cva(
  "inline-flex w-fit items-center rounded-pill px-3 py-1 font-body text-eyebrow uppercase",
  {
    variants: {
      tone: {
        soft: "bg-surface-soft text-accent",
        onInverse: "bg-white/10 text-text-accent-on-inverse",
        outline: "border border-border-hairline text-text-muted",
      },
    },
    defaultVariants: { tone: "soft" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
