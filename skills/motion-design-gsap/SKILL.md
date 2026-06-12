---
name: motion-design-gsap
description: Adds website motion design guidance for generated single-file HTML sites. Use when a generated page should include tasteful animation, scroll choreography, entrance motion, or micro-interactions using GSAP as the only animation framework. Not for CSS-only static pages or non-website animation tasks.
---

# Motion Design With GSAP

## Goal

Create motion that expresses the provided design system's energy without changing its layout, hierarchy, or component recipes. Motion should make the generated site feel finished, not like an animation demo.

## Implementation Rules

- Use GSAP as the only animation framework. Small plain JavaScript for selectors, guards, and event wiring is allowed.
- Include GSAP from a CDN in the single HTML file when animation is implemented.
- Use GSAP plugins only when they are part of the public GSAP distribution, such as ScrollTrigger. Do not rely on paid Club GSAP plugins.
- Respect `prefers-reduced-motion: reduce`: disable timeline motion, scroll-triggered movement, and looping ambient effects while preserving readable final states.
- Do not animate layout-critical properties that cause reflow. Prefer `opacity`, `transform`, CSS variables, and shader/canvas uniforms.
- Keep motion subtle enough that the page remains inspectable in a pipeline iframe screenshot.

## Motion Selection

1. Read the design system's stated rhythm, density, visual tension, and surface behavior.
2. Choose one motion attitude:
   - Calm systems: short fades, low-distance y movement, slow ambient drift.
   - Editorial or premium systems: staggered reveals, restrained parallax, text/image timing offsets.
   - Technical or futuristic systems: measured scan, orbit, grid, or data-flow motifs.
   - Playful systems: snappier easing, small overshoot, responsive hover/tap feedback.
3. Apply motion to recurring site structures, not every element.

## Required Patterns

- Initialize elements in final readable states for users without JavaScript.
- Add a motion-prep runtime hook in the document head before the first stylesheet can paint. Do not add the first `.js`/motion class from a footer script after the page has already rendered.
- For entrance reveals, prefer a safe three-step pattern: early head hook + CSS hidden prep state, `gsap.set()` to copy that start state inline once GSAP is available, then `gsap.to()` to animate to the final readable state. This avoids visible-then-hidden-then-visible flashes.
- Use `autoAlpha` or paired `opacity` and `visibility` for prepared hidden states so hidden interactive elements are not focusable/clickable before reveal. Always remove the prep hook and restore final states if GSAP is unavailable or reduced motion is requested.
- Use timeline labels or small named setup functions when more than one sequence exists.
- Keep entrance animations short: usually 0.45s-0.9s.
- Stagger repeated cards, stats, logos, or feature rows by small intervals.
- For hover/tap micro-interactions, animate only the interactive target and its local accent.
- Give each element one entrance-animation owner. Do not target the same element with both a generic utility reveal and a group stagger, and do not run multiple tweens that write competing `opacity`, `visibility`, or `transform` start values to the same element.

## No-FOUC Entrance Template

Use this structure, adapted to the page's actual selectors and distances, when adding scroll or load reveals:

```html
<head>
  <script>
    document.documentElement.classList.add('motion-prep');
  </script>
  <style>
    html.motion-prep [data-reveal] {
      opacity: 0;
      visibility: hidden;
      transform: translateY(24px);
    }
    @media (prefers-reduced-motion: reduce) {
      html.motion-prep [data-reveal] {
        opacity: 1;
        visibility: visible;
        transform: none;
      }
    }
  </style>
</head>
```

```js
(function () {
  var root = document.documentElement;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var revealEls = Array.from(document.querySelectorAll('[data-reveal]'));

  function showFinalState() {
    root.classList.remove('motion-prep');
    revealEls.forEach(function (el) {
      el.style.opacity = '';
      el.style.visibility = '';
      el.style.transform = '';
    });
  }

  if (reduce || !window.gsap || !revealEls.length) {
    showFinalState();
    return;
  }

  gsap.registerPlugin(ScrollTrigger);
  gsap.set(revealEls, { autoAlpha: 0, y: 24 });
  root.classList.remove('motion-prep');

  revealEls.forEach(function (el) {
    gsap.to(el, {
      autoAlpha: 1,
      y: 0,
      duration: 0.65,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: el,
        start: 'top 88%',
        once: true
      }
    });
  });

  window.addEventListener('load', function () {
    ScrollTrigger.refresh();
  });
})();
```

For grouped staggers, put `data-reveal-group` on the group and animate its children from one owner only. Do not also put `data-reveal` on those same children:

```js
gsap.utils.toArray('[data-reveal-group]').forEach(function (group) {
  var children = Array.from(group.children);
  gsap.set(children, { autoAlpha: 0, y: 18 });
  gsap.to(children, {
    autoAlpha: 1,
    y: 0,
    duration: 0.55,
    stagger: 0.08,
    ease: 'power2.out',
    scrollTrigger: { trigger: group, start: 'top 86%', once: true }
  });
});
```

## Avoid

- Framer Motion, Anime.js, AOS, ScrollReveal, Lottie libraries, or any animation framework besides GSAP.
- Giant page-loader animations that delay content.
- `gsap.from()` or `gsap.fromTo()` for ordinary opacity/transform entrance reveals on elements that may have already painted. From-type tweens render their start values immediately by default and can create a flash when scripts initialize late or when multiple tweens compete.
- Adding `.js`/motion CSS hidden states from a script near the end of `<body>`, which can produce a visible final state before the hidden state applies.
- Applying an entrance utility class to items that are also animated by a parent/group stagger.
- SplitText, MorphSVG, DrawSVG, or other paid GSAP plugins.
- Infinite motion on large text blocks or primary reading surfaces.
- Scroll effects that pin most of the page or fight natural document flow.

## Self-Check

Before outputting HTML:

- The page still works if JavaScript fails.
- Reduced-motion users get stable content.
- GSAP is the only animation framework.
- Motion reinforces the design system instead of adding a new aesthetic.
- There is no first-paint blink: animated elements are not visible in their final state before their entrance begins.
- Every entrance target has exactly one tween or timeline that owns its initial `opacity`/`visibility`/`transform` values.
