import { cn } from "@/lib/utils";

/*
  typography.display_numeral — oversized display metric used only for standalone
  figures. Pairs with a small label below; cells separate by hairline dividers
  (tokens.divider.verticalStat) in the stat band.
*/
export function Stat({
  value,
  label,
  className,
}: {
  value: string;
  label: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <span className="font-heading text-metric">{value}</span>
      <span className="font-body text-body text-text-muted">{label}</span>
    </div>
  );
}
