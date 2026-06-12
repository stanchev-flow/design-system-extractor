import { bestSrc, getByRole } from "@/brand/assets";

/** Resolves navigation/logo from harvested brand assets, with text fallback. */
export function BrandMark({ fallback = "Brand" }: { fallback?: string }) {
  const asset =
    getByRole("navigation/logo")[0] ??
    getByRole("navigation")[0] ??
    getByRole("footer")[0];
  if (!asset) {
    return <span className="text-h3 font-serif tracking-tight">{fallback}</span>;
  }
  if (asset.inlineSvg) {
    return (
      <span
        className="inline-flex h-8 w-auto [&_svg]:h-full [&_svg]:w-auto"
        dangerouslySetInnerHTML={{ __html: asset.inlineSvg }}
        aria-hidden
      />
    );
  }
  const src = bestSrc(asset);
  if (!src) {
    return <span className="text-h3 font-serif tracking-tight">{fallback}</span>;
  }
  return (
    <img
      src={src}
      alt={asset.alt || fallback}
      className="h-8 w-auto max-w-[200px] object-contain"
    />
  );
}
