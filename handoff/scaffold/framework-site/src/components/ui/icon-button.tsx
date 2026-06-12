import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/*
  components.icon_button_circular — fixed ~32px circle, icon only. Two grounded
  variants: a dark accent fill, and a hairline-bordered carousel control. The
  design system explicitly says: render the circle control, do not collapse it
  into a loose arrow glyph.
*/
const iconButtonVariants = cva(
  "grid place-items-center rounded-pill shrink-0 size-8 transition-colors duration-200 ease-out cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-40 disabled:pointer-events-none",
  {
    variants: {
      variant: {
        fill: "bg-accent text-accent-foreground hover:bg-[#16201a]",
        outline:
          "border border-border-hairline text-text-primary hover:bg-surface-secondary",
      },
    },
    defaultVariants: { variant: "outline" },
  }
);

export interface IconButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof iconButtonVariants> {}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton({ className, variant, ...props }, ref) {
    return (
      <button
        ref={ref}
        className={cn(iconButtonVariants({ variant }), className)}
        {...props}
      />
    );
  }
);
