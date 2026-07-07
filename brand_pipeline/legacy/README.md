# legacy/ — quarantined modules

## render_section.py (quarantined 2026-07-03, token-layer batch)

Retired per `experiments/token-layer-design/DECISIONS.md` #4: its 232 raw hardcode
hits predate the provenance-gated token layer and sit OUTSIDE `token-provenance`
scope. It was the ORIGINAL single-section renderer + the home of the shared token
resolvers.

- **Resolvers** (`color_value`, `type_role`, `spacing_value`, `base_size`, `css_len`,
  `font_stack`, `google_fonts_link`, `resolve_surface`, …) moved VERBATIM to
  `brand_pipeline/tokens_css.py` (the layer-1 generator module) — the new resolver
  single source of truth. All callers (`compose_section.py`, `compose_page.py`,
  `component_render.py`, `render_components_preview.py`) import from there now.
- **Single-section rendering** goes through `compose_section.py` (`build_document` /
  the compose CLI), which emits the generated `<style id="tokens">` layer-1 block +
  the `--c-*` alias layer.
- Nothing imports this module anymore. Do not add new imports; it is kept only as
  reference for the pre-token CSS template until the next cleanup pass deletes it.
