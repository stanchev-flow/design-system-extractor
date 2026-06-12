import * as React from "react";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

/*
  components.arrow_text_link — label + trailing circular arrow icon-button. This
  is the grounded SECONDARY action (lower emphasis than the primary pill), so it
  is a text link with a small circular arrow, never a filled button.
*/
export interface ArrowLinkProps
  extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  onInverse?: boolean;
}

export function ArrowLink({
  className,
  onInverse,
  children,
  ...props
}: ArrowLinkProps) {
  return (
    <a
      className={cn(
        "group inline-flex w-fit items-center gap-2 whitespace-nowrap font-body text-control font-medium transition-colors",
        onInverse ? "text-text-accent-on-inverse hover:text-white" : "text-accent hover:text-text-primary",
        className
      )}
      {...props}
    >
      <span>{children}</span>
      <span
        aria-hidden
        className={cn(
          "grid size-6 place-items-center rounded-pill border transition-transform group-hover:translate-x-0.5",
          onInverse ? "border-white/30" : "border-border-hairline"
        )}
      >
        <ArrowRight className="size-3.5" />
      </span>
    </a>
  );
}
