import * as React from "react";
import { cn } from "@/lib/utils";

/*
  Field recipe: label-above-field rhythm (rule: forms keep visible labels above
  inputs), field border token, md radius, body type.
*/
export interface FieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Field({ label, id, className, ...props }: FieldProps) {
  const fieldId = id ?? React.useId();
  return (
    <div className="flex flex-col gap-1.5 text-left">
      <label htmlFor={fieldId} className="font-body text-meta text-text-muted">
        {label}
      </label>
      <input
        id={fieldId}
        className={cn(
          "w-full rounded-md border border-border-field bg-surface-primary px-4 py-3 font-body text-body text-text-primary placeholder:text-text-muted/70 outline-none transition-colors focus-visible:border-accent",
          className
        )}
        {...props}
      />
    </div>
  );
}
