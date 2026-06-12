import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/*
  surfaces.* as a component. Each surface carries its own text-color context so
  child type/components inherit the correct on-surface colors. The grounded rule
  "page canvas owns edge/gutter continuity; tonal/inverse panels are child insets"
  is why inverse/soft are modeled as INSET PANELS (rounded, inset) rather than
  full-bleed section backgrounds — except `footer`, the one full-bleed reset.
*/
const surfaceVariants = cva("", {
  variants: {
    surface: {
      canvas: "bg-surface-primary text-text-primary",
      grain: "surface-grain text-text-primary",
      inverse: "bg-surface-inverse text-text-on-inverse",
      media: "bg-surface-media text-text-on-media",
    },
  },
  defaultVariants: { surface: "canvas" },
});

export interface SectionProps
  extends React.HTMLAttributes<HTMLElement>,
    VariantProps<typeof surfaceVariants> {
  tight?: boolean;
  /** Constrain content to the centered container inset (containerInset role). */
  contained?: boolean;
}

export function Section({
  className,
  surface,
  tight,
  contained = true,
  children,
  ...props
}: SectionProps) {
  return (
    <section
      className={cn(surfaceVariants({ surface }), tight ? "py-16" : "py-24", className)}
      {...props}
    >
      {contained ? <Container>{children}</Container> : children}
    </section>
  );
}

export function Container({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mx-auto w-full max-w-[1120px] px-6 md:px-10", className)}
      {...props}
    />
  );
}
