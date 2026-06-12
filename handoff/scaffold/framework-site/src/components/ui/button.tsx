import * as React from "react";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

/*
  Self-describing button. Instead of emitting a wall of utility classes, it
  renders one semantic `.btn` class plus its props as data-attributes:

      <button data-component="button" data-variant="primary" data-size="md" data-icon="trailing" class="btn">

  Why: the live element now carries its own state, so a controls panel (and AI)
  can READ the current variant/size/icon straight off the DOM and WRITE changes
  by flipping one attribute — no class parsing, no React state required. Styling
  lives once in index.css (@layer components), bound to design tokens.
*/

export type ButtonVariant = "primary" | "secondary" | "ghost" | "onMedia";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "type"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  withArrow?: boolean;
  htmlType?: "button" | "submit" | "reset";
}

export function Button({
  variant = "primary",
  size = "md",
  withArrow = false,
  htmlType = "button",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      data-component="button"
      data-variant={variant}
      data-size={size}
      data-icon={withArrow ? "trailing" : "none"}
      type={htmlType}
      className={cn("btn", className)}
      {...props}
    >
      <span>{children}</span>
      {/* chip is always present; CSS hides it when data-icon="none" */}
      <span aria-hidden className="btn-icon">
        <ArrowRight className="size-4" />
      </span>
    </button>
  );
}

/*
  The CONTROL CONTRACT. This is the machine-readable schema an inspector (or AI)
  reads to decide which controls to render when a `button` element is selected,
  and which attribute each control writes. This is the artifact the design-system
  pipeline would emit per component — derived from components[].variants / anatomy.
*/
export interface ControlField {
  name: string;
  label: string;
  control: "select" | "toggle";
  attr: string;
  options?: { value: string; label: string }[];
  on?: string;
  off?: string;
}

export interface ComponentSchema {
  component: string;
  label: string;
  fields: ControlField[];
}

export const buttonSchema: ComponentSchema = {
  component: "button",
  label: "Button",
  fields: [
    {
      name: "variant",
      label: "Type",
      control: "select",
      attr: "data-variant",
      options: [
        { value: "primary", label: "Primary" },
        { value: "secondary", label: "Secondary" },
        { value: "ghost", label: "Ghost" },
        { value: "onMedia", label: "On media" },
      ],
    },
    {
      name: "size",
      label: "Size",
      control: "select",
      attr: "data-size",
      options: [
        { value: "sm", label: "Small" },
        { value: "md", label: "Medium" },
        { value: "lg", label: "Large" },
      ],
    },
    {
      name: "icon",
      label: "Trailing icon",
      control: "toggle",
      attr: "data-icon",
      on: "trailing",
      off: "none",
    },
  ],
};
