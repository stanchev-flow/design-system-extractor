import { bestSrc, brandLogo, brandName } from "@/brand/assets";

/** Resolves the brand's own mark from harvested assets, with text fallback.
 *  The fallback is the BRAND's name: an extraction that never captured a
 *  wordmark should still read as this brand, not as the word "Brand". */
export function BrandMark({
  fallback,
  className = "",
}: {
  fallback?: string;
  className?: string;
} = {}) {
  const label = fallback || brandName || "Brand";
  const asset = brandLogo();
  const text = `text-h3 font-serif tracking-tight ${className}`.trim();
  if (!asset) {
    return <span className={text}>{label}</span>;
  }
  if (asset.inlineSvg) {
    return (
      <span
        className={`inline-flex h-8 w-auto [&_svg]:h-full [&_svg]:w-auto ${className}`.trim()}
        dangerouslySetInnerHTML={{ __html: asset.inlineSvg }}
        aria-hidden
      />
    );
  }
  const src = bestSrc(asset);
  if (!src) {
    return <span className={text}>{label}</span>;
  }
  return (
    <img
      src={src}
      alt={asset.alt || label}
      className={`h-8 w-auto max-w-[200px] object-contain ${className}`.trim()}
    />
  );
}
