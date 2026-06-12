import { useCallback, useEffect, useState } from "react";
import { Settings2, Sparkles, X } from "lucide-react";
import {
  buttonSchema,
  type ComponentSchema,
  type ControlField,
} from "@/components/ui/button";

/*
  CONTEXT-BASED CONTROLS prototype.

  Click any element that declares `data-component` and the inspector looks up its
  schema, reads the element's current data-attributes, and renders exactly the
  controls that component supports. Changing a control writes the attribute back
  on that specific element — the element is the source of truth, the panel is
  just a typed view over it. This is the model an AI editor would drive:
    1. identity  -> data-component="button"
    2. schema    -> buttonSchema (what can change + which attr each control writes)
    3. intent    -> the "describe the change" box maps text -> schema-valid edits
*/

const SCHEMAS: Record<string, ComponentSchema> = {
  button: buttonSchema,
};

/* Stand-in for the LLM intent->schema step. A real build sends the prompt + the
   active schema to the model and gets back attribute edits; here we resolve a few
   phrases locally so the prototype runs with no key. */
function resolveIntent(
  text: string,
  schema: ComponentSchema
): { attr: string; value: string; label: string }[] {
  const t = text.toLowerCase();
  const edits: { attr: string; value: string; label: string }[] = [];
  const push = (field: ControlField, value: string) =>
    edits.push({ attr: field.attr, value, label: `${field.label} → ${value}` });

  const variant = schema.fields.find((f) => f.name === "variant");
  const size = schema.fields.find((f) => f.name === "size");
  const icon = schema.fields.find((f) => f.name === "icon");

  if (variant) {
    if (/secondary|outline|bordered/.test(t)) push(variant, "secondary");
    else if (/ghost|text|subtle|minimal|low.?emphasis/.test(t)) push(variant, "ghost");
    else if (/on.?media|over.?image|on.?dark/.test(t)) push(variant, "onMedia");
    else if (/primary|solid|filled|main/.test(t)) push(variant, "primary");
  }
  if (size) {
    if (/larger|bigger|\blarge\b|\blg\b|\bbig\b|prominent/.test(t)) push(size, "lg");
    else if (/smaller|\bsmall\b|\bsm\b|compact|tiny/.test(t)) push(size, "sm");
    else if (/medium|\bmd\b|default|normal/.test(t)) push(size, "md");
  }
  if (icon) {
    if (/(no|remove|without|drop).{0,14}(icon|arrow)|hide arrow/.test(t))
      push(icon, icon.off ?? "none");
    else if (/(add|with|show).{0,14}(icon|arrow)|trailing/.test(t))
      push(icon, icon.on ?? "trailing");
  }
  return edits;
}

export function Inspector() {
  const [el, setEl] = useState<HTMLElement | null>(null);
  const [intent, setIntent] = useState("");
  const [lastApplied, setLastApplied] = useState<string[]>([]);
  const [, force] = useState(0);
  const rerender = useCallback(() => force((n) => n + 1), []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      if (target.closest("[data-inspector]")) return; // clicks inside the panel
      const comp = target.closest("[data-component]") as HTMLElement | null;
      if (comp && SCHEMAS[comp.getAttribute("data-component") ?? ""]) {
        // in edit mode we select instead of activating the control
        e.preventDefault();
        e.stopPropagation();
        setEl((prev) => {
          if (prev && prev !== comp) prev.removeAttribute("data-selected");
          comp.setAttribute("data-selected", "true");
          return comp;
        });
        setLastApplied([]);
      } else {
        setEl((prev) => {
          if (prev) prev.removeAttribute("data-selected");
          return null;
        });
      }
    }
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, []);

  function close() {
    if (el) el.removeAttribute("data-selected");
    setEl(null);
  }

  function setAttr(attr: string, value: string) {
    if (!el) return;
    el.setAttribute(attr, value);
    rerender();
  }

  function applyIntent() {
    if (!el || !intent.trim()) return;
    const schema = SCHEMAS[el.getAttribute("data-component") ?? ""];
    const edits = resolveIntent(intent, schema);
    edits.forEach((edit) => el.setAttribute(edit.attr, edit.value));
    setLastApplied(edits.map((edit) => edit.label));
    rerender();
  }

  const schema = el ? SCHEMAS[el.getAttribute("data-component") ?? ""] : null;

  return (
    <aside
      data-inspector
      className="fixed bottom-4 right-4 z-[100] w-[300px] overflow-hidden rounded-xl border border-border-hairline bg-surface-primary shadow-2xl"
      style={{ fontFamily: "var(--font-body)" }}
    >
      <div className="flex items-center justify-between border-b border-border-hairline px-4 py-3">
        <div className="flex items-center gap-2">
          <Settings2 className="size-4 text-accent" />
          <span className="text-control font-medium text-text-primary">
            {schema ? schema.label : "Inspector"}
          </span>
        </div>
        {el ? (
          <button
            onClick={close}
            className="grid size-6 place-items-center rounded-md text-text-muted hover:bg-surface-secondary"
            aria-label="Deselect"
          >
            <X className="size-4" />
          </button>
        ) : null}
      </div>

      {!el || !schema ? (
        <p className="px-4 py-5 text-meta leading-relaxed text-text-muted">
          Click any <span className="font-medium text-text-primary">button</span>{" "}
          on the page to edit it. Controls are generated from that component's
          schema.
        </p>
      ) : (
        <div className="flex flex-col gap-4 px-4 py-4">
          <p className="text-meta text-text-muted">
            Selected{" "}
            <code className="rounded bg-surface-secondary px-1 py-0.5 text-text-primary">
              {`<button data-component="button">`}
            </code>
          </p>

          {schema.fields.map((field) => {
            const current = el.getAttribute(field.attr) ?? "";
            if (field.control === "select") {
              return (
                <label key={field.name} className="flex flex-col gap-1.5">
                  <span className="text-meta font-medium text-text-muted">
                    {field.label}
                  </span>
                  <select
                    value={current}
                    onChange={(e) => setAttr(field.attr, e.target.value)}
                    className="h-9 rounded-md border border-border-hairline bg-surface-primary px-2 text-control text-text-primary focus:outline-2 focus:outline-accent"
                  >
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>
              );
            }
            // toggle
            const isOn = current === field.on;
            return (
              <div key={field.name} className="flex items-center justify-between">
                <span className="text-meta font-medium text-text-muted">
                  {field.label}
                </span>
                <button
                  onClick={() =>
                    setAttr(field.attr, isOn ? field.off ?? "" : field.on ?? "")
                  }
                  role="switch"
                  aria-checked={isOn}
                  className={`relative h-6 w-11 rounded-pill transition-colors ${
                    isOn ? "bg-accent" : "bg-border-hairline"
                  }`}
                >
                  <span
                    className={`absolute top-0.5 size-5 rounded-pill bg-surface-primary transition-all ${
                      isOn ? "left-[22px]" : "left-0.5"
                    }`}
                  />
                </button>
              </div>
            );
          })}

          <div className="flex flex-col gap-2 border-t border-border-hairline pt-3">
            <span className="flex items-center gap-1.5 text-meta font-medium text-text-muted">
              <Sparkles className="size-3.5 text-accent" /> Describe the change
            </span>
            <textarea
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              placeholder="e.g. make it secondary and larger, no icon"
              rows={2}
              className="resize-none rounded-md border border-border-hairline bg-surface-primary px-2 py-1.5 text-control text-text-primary focus:outline-2 focus:outline-accent"
            />
            <button
              onClick={applyIntent}
              className="btn"
              data-variant="primary"
              data-size="sm"
              data-icon="none"
            >
              Apply
            </button>
            {lastApplied.length > 0 ? (
              <p className="text-meta text-text-muted">
                Applied: {lastApplied.join(", ")}
              </p>
            ) : null}
          </div>
        </div>
      )}
    </aside>
  );
}
