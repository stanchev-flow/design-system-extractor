import data from "./brand-assets.json";

/*
  Asset resolver — MEASURED BINDING FIRST.

  When the bundle comes from a brand extraction, every asset carries the
  sections it was measured rendering in. A page asks for the assets of a BAND
  (`sectionAssets("home-section-02-div")`) and gets exactly what the source used,
  in the source's visual order.

  Only when a composition is genuinely NEW (no source band to copy) does it fall
  back to `roleAssets`, which returns assets by the geometric role they were
  measured playing — a proof-strip mark stays a proof-strip mark and never gets
  promoted into a hero well because its aspect ratio happened to look right.

  Assets with `reusePolicy: "unplaced"` were curated but never observed
  rendering, so they are UNPROVEN and are withheld from every lookup.
*/

export interface AssetPlacement {
  page: string;
  section: string | null;
  zone: string;
  role: string;
  visible: boolean;
}

export interface BrandAsset {
  id: string;
  file?: string;
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
  usageRights?: string;
  reusePolicy?: string;
  compositionRoles?: string[];
  placements?: AssetPlacement[];
}

type ByRole = Record<string, BrandAsset[]>;

const bundle = data as {
  source?: string;
  brand?: { name?: string; wordmarkUrl?: string };
  assets?: BrandAsset[];
  bySection?: Record<string, string[]>;
  byRole?: ByRole;
};

const byRole: ByRole = bundle.byRole ?? {};
const bySection = bundle.bySection ?? {};
const allAssets = bundle.assets ?? Object.values(byRole).flat();
const byId = new Map(allAssets.map((a) => [a.id, a]));
// The brand artifacts (layout slots, section inventories) name assets by FILE,
// while the bundle keys them by id. Both identify the same asset, so a lookup
// accepts either — a resolver that fails on the artifact's own vocabulary just
// silently drops the image.
const byFile = new Map(
  allAssets.flatMap((a) => (a.file ? ([[a.file, a]] as [string, BrandAsset][]) : []))
);

export const brandSource = bundle.source ?? "";
/** The brand's own name — the honest wordmark fallback when no mark was curated. */
export const brandName = bundle.brand?.name ?? "";
/** The chrome wordmark file, when the extraction captured one. */
export const brandWordmarkUrl = bundle.brand?.wordmarkUrl ?? "";

function renderable(a: BrandAsset | undefined): a is BrandAsset {
  return !!a && !!(a.url || a.inlineSvg) && a.reusePolicy !== "unplaced";
}

/** The assets MEASURED in one source band, in the source's visual order. */
export function sectionAssets(section: string): BrandAsset[] {
  return (bySection[section] ?? []).map((id) => byId.get(id)).filter(renderable);
}

/** Assets measured playing a given composition role (for NEW compositions). */
export function roleAssets(role: string, limit?: number): BrandAsset[] {
  const out = (byRole[role] ?? []).filter(renderable);
  return limit ? out.slice(0, limit) : out;
}

/** One asset by its registry id OR its filename (both name the same asset). */
export function assetById(ref: string): BrandAsset | null {
  const a = byId.get(ref) ?? byFile.get(ref);
  return renderable(a) ? a : null;
}

/** The brand's OWN mark — identified by kind, never by which surface it sat on.
 *  Picking "the first chrome image" would hand back a nav menu thumbnail. */
export function brandLogo(): BrandAsset | null {
  if (brandWordmarkUrl) {
    return {
      id: "brand-wordmark",
      type: "logo-own",
      role: "navigation/logo",
      label: brandName,
      alt: brandName,
      url: brandWordmarkUrl,
      displayUrl: brandWordmarkUrl,
      inlineSvg: "",
      iconOrIllustration: "na",
      width: null,
      height: null,
      aspect: null,
    };
  }
  const own = allAssets.filter(
    (a) => renderable(a) && (a.type === "logo-own" || a.role === "navigation/logo")
  );
  if (own.length) return own[0];
  const legacy = (byRole["navigation/logo"] ?? byRole["navigation"] ?? []).filter(renderable);
  return legacy[0] ?? null;
}

/** Third-party marks may only appear as attribution/proof, never as decoration. */
export function isThirdPartyMark(a: BrandAsset | null | undefined): boolean {
  return !!a && a.usageRights === "third-party-mark";
}

export function bestSrc(a: BrandAsset | null | undefined): string {
  if (!a) return "";
  return a.displayUrl || a.url || "";
}
