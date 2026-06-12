import * as React from "react";
import useEmblaCarousel, {
  type UseEmblaCarouselType,
} from "embla-carousel-react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { IconButton } from "@/components/ui/icon-button";
import type { ComponentSchema } from "@/components/ui/button";

/*
  components.carousel — Tier 1 slider primitive. Engine: Embla.

  Why Embla over Swiper / Smooothy in this stack:
    - Headless: no foreign DOM/CSS. Item layout is owned by Tailwind utilities,
      so every grounded value (gap, item width, peek, snap) lives in JSX, not in
      a library theme override.
    - ~6KB core + composable plugins (autoplay, fade, wheel-gestures), so feature
      ceiling is driven by what the grounded design system actually asked for.
    - A11y baseline: aria-roledescription="carousel"/"slide", keyboard arrows,
      respects RTL, plays nicely with prefers-reduced-motion via opts.duration.

  Why this file reuses IconButton: icon-button.tsx's `outline` variant is the
  grounded "hairline-bordered carousel control" recipe. Carousel arrows MUST be
  rendered as circular controls, not loose glyphs (see surface-component-map
  -strategy.md L184 and L35 of website-gen-prompt.md). One source of truth.

  Anatomy (consumer side):
      <Carousel opts={{ align: "start", loop: false }}>
        <CarouselContent>
          <CarouselItem className="basis-full md:basis-1/2 lg:basis-1/3">…</CarouselItem>
          …
        </CarouselContent>
        <CarouselPrevious />
        <CarouselNext />
      </Carousel>

  The grounded carousel contract (components.slider) maps to this surface 1:1:
      personality: content    → align: "start", loop: false, basis-1/N items
      personality: showcase   → align: "center", basis-full, larger gap
      personality: marquee    → autoplay plugin + loop: true, no controls
*/

type CarouselApi = UseEmblaCarouselType[1];
type UseCarouselParameters = Parameters<typeof useEmblaCarousel>;
type CarouselOptions = UseCarouselParameters[0];
type CarouselPlugin = UseCarouselParameters[1];

export type CarouselOrientation = "horizontal" | "vertical";

export interface CarouselProps {
  opts?: CarouselOptions;
  plugins?: CarouselPlugin;
  orientation?: CarouselOrientation;
  setApi?: (api: CarouselApi) => void;
}

type CarouselContextValue = {
  carouselRef: ReturnType<typeof useEmblaCarousel>[0];
  api: CarouselApi;
  scrollPrev: () => void;
  scrollNext: () => void;
  canScrollPrev: boolean;
  canScrollNext: boolean;
  orientation: CarouselOrientation;
};

const CarouselContext = React.createContext<CarouselContextValue | null>(null);

function useCarousel() {
  const ctx = React.useContext(CarouselContext);
  if (!ctx) {
    throw new Error("useCarousel must be used within a <Carousel />.");
  }
  return ctx;
}

export const Carousel = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & CarouselProps
>(function Carousel(
  {
    orientation = "horizontal",
    opts,
    setApi,
    plugins,
    className,
    children,
    ...props
  },
  ref
) {
  const [carouselRef, api] = useEmblaCarousel(
    { ...opts, axis: orientation === "horizontal" ? "x" : "y" },
    plugins
  );
  const [canScrollPrev, setCanScrollPrev] = React.useState(false);
  const [canScrollNext, setCanScrollNext] = React.useState(false);

  const onSelect = React.useCallback((embla: CarouselApi) => {
    if (!embla) return;
    setCanScrollPrev(embla.canScrollPrev());
    setCanScrollNext(embla.canScrollNext());
  }, []);

  const scrollPrev = React.useCallback(() => api?.scrollPrev(), [api]);
  const scrollNext = React.useCallback(() => api?.scrollNext(), [api]);

  const handleKeyDown = React.useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        scrollPrev();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        scrollNext();
      }
    },
    [scrollPrev, scrollNext]
  );

  React.useEffect(() => {
    if (!api || !setApi) return;
    setApi(api);
  }, [api, setApi]);

  React.useEffect(() => {
    if (!api) return;
    onSelect(api);
    api.on("reInit", onSelect);
    api.on("select", onSelect);
    return () => {
      api.off("select", onSelect);
      api.off("reInit", onSelect);
    };
  }, [api, onSelect]);

  return (
    <CarouselContext.Provider
      value={{
        carouselRef,
        api,
        scrollPrev,
        scrollNext,
        canScrollPrev,
        canScrollNext,
        orientation,
      }}
    >
      <div
        ref={ref}
        data-component="carousel"
        data-orientation={orientation}
        onKeyDownCapture={handleKeyDown}
        className={cn("relative", className)}
        role="region"
        aria-roledescription="carousel"
        {...props}
      >
        {children}
      </div>
    </CarouselContext.Provider>
  );
});

export const CarouselContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(function CarouselContent({ className, ...props }, ref) {
  const { carouselRef, orientation } = useCarousel();
  return (
    <div ref={carouselRef} className="overflow-hidden">
      <div
        ref={ref}
        className={cn(
          "flex",
          orientation === "horizontal" ? "-ml-4" : "-mt-4 flex-col",
          className
        )}
        {...props}
      />
    </div>
  );
});

export const CarouselItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(function CarouselItem({ className, ...props }, ref) {
  const { orientation } = useCarousel();
  return (
    <div
      ref={ref}
      role="group"
      aria-roledescription="slide"
      className={cn(
        // Default: one slide per viewport. Override with basis-1/2, basis-1/3, etc.
        "min-w-0 shrink-0 grow-0 basis-full",
        orientation === "horizontal" ? "pl-4" : "pt-4",
        className
      )}
      {...props}
    />
  );
});

/*
  Previous / Next: the grounded "circular icon-action" recipe. We render
  IconButton (outline by default) and absolutely position it relative to the
  Carousel root. Consumers can override placement via className.
*/

export interface CarouselNavProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "outline" | "fill";
}

export const CarouselPrevious = React.forwardRef<
  HTMLButtonElement,
  CarouselNavProps
>(function CarouselPrevious(
  { className, variant = "outline", ...props },
  ref
) {
  const { orientation, scrollPrev, canScrollPrev } = useCarousel();
  return (
    <IconButton
      ref={ref}
      variant={variant}
      type="button"
      aria-label="Previous slide"
      disabled={!canScrollPrev}
      onClick={scrollPrev}
      className={cn(
        "absolute",
        orientation === "horizontal"
          ? "left-2 top-1/2 -translate-y-1/2"
          : "left-1/2 top-2 -translate-x-1/2 rotate-90",
        className
      )}
      {...props}
    >
      <ArrowLeft className="size-4" />
    </IconButton>
  );
});

export const CarouselNext = React.forwardRef<
  HTMLButtonElement,
  CarouselNavProps
>(function CarouselNext({ className, variant = "outline", ...props }, ref) {
  const { orientation, scrollNext, canScrollNext } = useCarousel();
  return (
    <IconButton
      ref={ref}
      variant={variant}
      type="button"
      aria-label="Next slide"
      disabled={!canScrollNext}
      onClick={scrollNext}
      className={cn(
        "absolute",
        orientation === "horizontal"
          ? "right-2 top-1/2 -translate-y-1/2"
          : "left-1/2 bottom-2 -translate-x-1/2 rotate-90",
        className
      )}
      {...props}
    >
      <ArrowRight className="size-4" />
    </IconButton>
  );
});

export type { CarouselApi };

/*
  CONTROL CONTRACT — same pattern as buttonSchema. The inspector / AI reads this
  to render controls for a selected carousel and writes back via data-attributes.
  Personality is the grounded handle from components.slider.personality.
*/

export const carouselSchema: ComponentSchema = {
  component: "carousel",
  label: "Carousel",
  fields: [
    {
      name: "orientation",
      label: "Orientation",
      control: "select",
      attr: "data-orientation",
      options: [
        { value: "horizontal", label: "Horizontal" },
        { value: "vertical", label: "Vertical" },
      ],
    },
  ],
};
