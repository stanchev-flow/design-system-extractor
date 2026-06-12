import data from "./brand-assets.json";

/*
  Role-based asset resolver with SLOT-AWARE RANKING.

  A generated page asks for assets by the ROLE they play ("a hero media",
  "testimonial avatars", "the logo wall"). Each request carries a SlotSpec —
  the preferred asset types plus the geometry the slot wants (ideal aspect,
  minimum width). Candidates are scored on type fit + aspect closeness + size
  adequacy, so each slot gets the BEST-fitting brand asset, not just the first.
*/

export interface BrandAsset {
  id: string;
  type: string;
  role: string;
  label: string;
  alt: string;
  url: string;
  displayUrl: string;
  inlineSvg: string;
  iconOrIllustration: string;
  width: number | null;
  height: number | null;
  aspect: number | null;
}

interface SlotSpec {
  roles: string[];
  prefTypes: string[];
  idealAspect?: number;
  minWidth?: number;
}

type ByRole = Record<string, BrandAsset[]>;

const byRole = (data as { byRole: ByRole }).byRole;
export const brandSource = (data as { source: string }).source;

export function getByRole(role: string): BrandAsset[] {
  return byRole[role] ?? [];
}

export function bestSrc(a: BrandAsset | null | undefined): string {
  if (!a) return "";
  return a.displayUrl || a.url || "";
}

function score(a: BrandAsset, spec: SlotSpec): number {
  let s = 0;

  // Type fit: earlier in prefTypes ranks higher; unlisted types are penalized.
  const ti = spec.prefTypes.indexOf(a.type);
  s += ti >= 0 ? (spec.prefTypes.length - ti) * 2 : -2;

  // Aspect closeness (only when we measured real dimensions).
  if (spec.idealAspect && a.aspect) {
    const closeness = 1 - Math.min(1, Math.abs(a.aspect - spec.idealAspect) / spec.idealAspect);
    s += closeness * 4;
  }

  // Size adequacy: reward meeting the slot's minimum, lightly reward bigger.
  if (a.width) {
    if (spec.minWidth) s += a.width >= spec.minWidth ? 1.5 : -1;
    s += Math.min(1, a.width / 1600);
  }

  return s;
}

function rank(spec: SlotSpec, limit?: number): BrandAsset[] {
  const seen = new Set<string>();
  const pool: BrandAsset[] = [];
  for (const role of spec.roles) {
    for (const a of getByRole(role)) {
      if (a.url && !seen.has(a.id)) {
        seen.add(a.id);
        pool.push(a);
      }
    }
  }
  const scored = pool.map((a, i) => ({ a, i, s: score(a, spec) }));
  scored.sort((x, y) => y.s - x.s || x.i - y.i); // stable tie-break by source order
  const out = scored.map((x) => x.a);
  return limit ? out.slice(0, limit) : out;
}

export function heroMedia(): BrandAsset | null {
  return (
    rank(
      { roles: ["hero", "card/feature", "content", "background"], prefTypes: ["illustration", "photo"], idealAspect: 1.4, minWidth: 600 },
      1
    )[0] ?? null
  );
}

export function avatars(limit = 3): BrandAsset[] {
  return rank(
    { roles: ["testimonial/avatar", "content"], prefTypes: ["avatar", "photo"], idealAspect: 1.0 },
    limit
  );
}

export function logoWall(limit = 12): BrandAsset[] {
  return rank({ roles: ["logo-wall", "content"], prefTypes: ["logo"] }, limit);
}

export function ctaBackground(): BrandAsset | null {
  return (
    rank(
      { roles: ["background", "card/feature", "hero", "content"], prefTypes: ["background", "photo"], idealAspect: 1.8, minWidth: 1000 },
      1
    )[0] ?? null
  );
}

export function featureMedia(limit = 3): BrandAsset[] {
  return rank(
    { roles: ["card/feature", "hero", "content"], prefTypes: ["illustration", "photo"], idealAspect: 1.3 },
    limit
  );
}
