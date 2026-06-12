/**
 * Style Dictionary config — compiles tokens/tokens.json (DTCG) into the
 * Tailwind v4 theme layer (src/tokens.generated.css). Run with `npm run tokens`.
 *
 * The same token source can target other platforms by adding files here, e.g.
 * a `json` Webflow-variables payload, iOS `.swift`, or Android `.xml`. That is
 * the whole point of keeping tokens framework-agnostic: one source, many emits.
 *
 * NOTE: src/index.css ships a hand-mirrored @theme so the project builds without
 * running this step; this config documents (and reproduces) that generation.
 */
export default {
  source: ["tokens/tokens.json"],
  platforms: {
    tailwind: {
      transformGroup: "css",
      buildPath: "src/",
      files: [
        {
          destination: "tokens.generated.css",
          format: "css/variables",
          options: { selector: "@theme", outputReferences: true },
        },
      ],
    },
  },
};
