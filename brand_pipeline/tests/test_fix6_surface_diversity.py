"""fix6 — copy-first event rebuild + gallery surface diversity.

Law under test:
  1. SURFACE SELECTION is part of the copy-first layout plan (spec/archetype-library.md
     §3): creative hero mode replaces the whole-page rhythm MANDATE ("opens dark ⇒ the
     hero MUST be inverse" — the fix6 root cause: 8/8 gallery heroes forced onto one
     dark role) with the brand's own licensed surface ROSTER + a gallery-variety
     consideration. Replica-shaped composition paths stay byte-identical.
  2. `surfaceIntent` generalizes beyond the canonical five: any brand-declared
     tokens.surfaces role suffix resolves (`surface/<value>`); unknown suffixes keep
     the historical degrade (never an invented surface).
  3. GENRE-SKELETON heroes are slot-faithful end to end: archetype slot NAMES ride as
     copy fallbacks, unauthored slots render EMPTY (no SECTION_COPY ride-through), an
     actionGroup slot with list copy expands to real actions, and a logo-family slot
     maps as the mark rail.
"""
from __future__ import annotations

import copy as _copylib
import json
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import compose_from_composition as cfc    # noqa: E402
import compose_section as cs              # noqa: E402
import generate_composition as gc         # noqa: E402

REPO = HERE.parent
HUBSPOT = REPO / "runs" / "hubspot-v2" / "brand" / "brand.yaml"
sys.path.insert(0, str(REPO / "tools"))

import run_hero_archetype_gallery as runner    # noqa: E402


def _hubspot_doc():
    return yaml.safe_load(HUBSPOT.read_text())


class CreativeSurfaceRules(unittest.TestCase):
    """_brand_fidelity_rules: roster in creative hero mode, mandate elsewhere."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _hubspot_doc()

    def test_replica_path_keeps_the_rhythm_mandate(self):
        out = gc._brand_fidelity_rules(self.doc, True)
        self.assertIn("MUST use `surfaceIntent: \"inverse\"`", out)
        self.assertNotIn("SURFACE SELECTION", out)
        # default None == explicit None (byte-identical replica path)
        self.assertEqual(out, gc._brand_fidelity_rules(self.doc, True,
                                                       creative_hero_used=None))

    def test_creative_mode_offers_the_licensed_roster_not_a_mandate(self):
        out = gc._brand_fidelity_rules(self.doc, True, creative_hero_used=[])
        self.assertIn("SURFACE SELECTION", out)
        self.assertNotIn("MUST use `surfaceIntent: \"inverse\"`", out)
        # every declared surface role suffix is offered
        for suffix in ("primary", "panel", "raised", "accent-wash",
                       "inverse", "inverse-strong", "photo-hero"):
            self.assertIn(f'"{suffix}"', out)
        # nesting facts ride into the rule block
        self.assertIn("surface/panel may nest ONLY on", out)

    def test_dark_markers_follow_scheme_mode_not_role_name(self):
        out = gc._brand_fidelity_rules(self.doc, True, creative_hero_used=[])
        # accent-wash is a LIGHT art band (schemeMode base) despite "accent" in its name
        self.assertIn('"accent-wash" —', out)
        self.assertNotIn('"accent-wash" (dark)', out)
        self.assertIn('"photo-hero" (dark)', out)

    def test_variety_block_lists_sibling_choices(self):
        out = gc._brand_fidelity_rules(self.doc, True,
                                       creative_hero_used=["inverse", "inverse", "raised"])
        self.assertIn("GALLERY VARIETY", out)
        self.assertIn('"inverse" ×2', out)
        self.assertIn('"raised"', out)
        # no used surfaces -> no variety paragraph, roster still present
        out2 = gc._brand_fidelity_rules(self.doc, True, creative_hero_used=[])
        self.assertNotIn("GALLERY VARIETY", out2)

    def test_brand_without_dark_surface_stays_forbidden(self):
        doc = {"tokens": {"surfaces": {
            "surface/primary": {"bg": "#fff", "schemeMode": "base", "intent": "canvas"},
            "surface/panel": {"bg": "#fafafa", "schemeMode": "Container", "intent": "card"},
        }}}
        out = gc._brand_fidelity_rules(doc, True, creative_hero_used=[])
        self.assertIn("declares NO dark surface", out)


class SurfaceIntentGeneralization(unittest.TestCase):
    """Non-canonical surfaceIntent values resolve to brand-declared roles only."""

    def test_canonical_values_map_exactly_as_before(self):
        for intent, role in (("any", "surface/primary"), ("primary", "surface/primary"),
                             ("inverse", "surface/inverse"), ("panel", "surface/panel"),
                             ("inverse-strong", "surface/inverse-strong")):
            layout = cfc.composition_to_layout(
                {"id": "s", "archetype": "stack", "surfaceIntent": intent, "slots": []})
            self.assertEqual(layout["surfaceIntent"], role, intent)

    def test_brand_declared_suffix_resolves_and_renders(self):
        layout = cfc.composition_to_layout(
            {"id": "s", "archetype": "stack", "surfaceIntent": "raised", "slots": []})
        self.assertEqual(layout["surfaceIntent"], "surface/raised")
        role, surf = cs.resolve_surface_intent(_hubspot_doc(), layout)
        self.assertEqual(role, "surface/raised")
        self.assertEqual(surf["bg"], "#f8f5ee")

    def test_unknown_suffix_keeps_the_historical_degrade(self):
        layout = cfc.composition_to_layout(
            {"id": "s", "archetype": "stack", "surfaceIntent": "moonlight", "slots": []})
        role, _ = cs.resolve_surface_intent(_hubspot_doc(), layout)
        doc = _hubspot_doc()
        self.assertEqual(role, next(iter(doc["tokens"]["surfaces"])))

    def test_schema_accepts_role_suffixes_and_rejects_shapes(self):
        import re
        schema = json.loads((HERE / "spec" / "composition.v1.schema.json").read_text())
        pattern = schema["$defs"]["surfaceIntent"]["pattern"]
        for ok in ("any", "primary", "inverse-strong", "raised", "accent-wash", "photo-hero"):
            self.assertTrue(re.fullmatch(pattern, ok), ok)
        for bad in ("Raised", "surface/raised", "", "#042729", "a b"):
            self.assertFalse(re.fullmatch(pattern, bad), bad)


def _event_like_section(**over):
    sec = {
        "id": "spotlight-hero", "useCase": "hero", "archetype": "stack",
        "surfaceIntent": "raised", "novelty": "adapt",
        "archetypeRef": "hero-event-meta-forward",
        "slots": [
            {"name": "meta", "role": "event-logistics", "contract": "label",
             "copy": "Oct 8, 2026 · 9:00 AM ET"},
            {"name": "heading", "role": "event-name", "contract": "heading",
             "copy": "Spotlight"},
            {"name": "subheading", "role": "promise", "contract": "paragraph",
             "copy": "The fall reveal — live."},
            {"name": "actionGroup", "role": "register-actions", "contract": "button",
             "copy": [{"label": "Save my seat", "emphasis": "primary"},
                      {"label": "See the fall lineup", "emphasis": "secondary"}]},
            {"name": "agenda", "role": "agenda-rail", "contract": "logo-bar",
             "copy": {"caption": "90 minutes across every Hub.",
                      "logos": [{"alt": "Marketing Hub",
                                 "asset": {"src": "assets/028-producticons-marketinghub-icon-orange.webp"}},
                                {"alt": "Sales Hub",
                                 "asset": {"src": "assets/029-producticons-saleshub-icon-orange.webp"}}]}},
        ],
    }
    sec.update(over)
    return sec


class SlotFaithfulHeroCopy(unittest.TestCase):
    """_hero_section_copy: archetype slot-name fallbacks + ride-through suppression."""

    def test_archetype_meta_and_promise_bind_by_slot_name(self):
        out = cfc._hero_section_copy(_event_like_section())
        self.assertEqual(out["eyebrow"], "Oct 8, 2026 · 9:00 AM ET")
        self.assertEqual(out["subhead"], "The fall reveal — live.")

    def test_archetype_unauthored_slots_render_empty_not_brand_defaults(self):
        sec = _event_like_section()
        sec["slots"] = [s for s in sec["slots"]
                        if s["name"] not in ("meta", "subheading")]
        out = cfc._hero_section_copy(sec)
        self.assertEqual(out["eyebrow"], "")
        self.assertEqual(out["subhead"], "")

    def test_non_archetype_sections_keep_the_legacy_defaults(self):
        sec = _event_like_section()
        sec.pop("archetypeRef")
        sec["slots"] = [s for s in sec["slots"] if s["name"] == "heading"]
        out = cfc._hero_section_copy(sec)
        # legacy heroes leave the keys UNSET so the brand's own section-copy layer
        # rides at copy_for (the pre-fix6 behavior, byte-identical)
        self.assertNotIn("eyebrow", out)
        self.assertNotIn("subhead", out)


class ActionGroupAndRailMapping(unittest.TestCase):
    """_hero_mapping: list-copy actionGroup expansion + the logo-family mark rail."""

    def test_action_group_list_expands_to_real_buttons(self):
        mapping = cfc._hero_mapping(_event_like_section())
        buttons = [m for m in mapping if m["contract"] == "button"]
        self.assertEqual([b["usage"]["label"] for b in buttons],
                         ["Save my seat", "See the fall lineup"])
        self.assertNotIn("styleHint", buttons[0]["usage"])
        self.assertEqual(buttons[1]["usage"]["styleHint"], "secondary")

    def test_logo_slot_maps_as_rail_marks_plus_caption(self):
        mapping = cfc._hero_mapping(_event_like_section())
        marks = [m for m in mapping if str(m["role"]).startswith("rail mark")]
        caps = [m for m in mapping if str(m["role"]).startswith("rail caption")]
        self.assertEqual(len(marks), 2)
        self.assertEqual(marks[0]["usage"]["src"],
                         "assets/028-producticons-marketinghub-icon-orange.webp")
        self.assertEqual(len(caps), 1)
        self.assertEqual(caps[0]["usage"]["text"], "90 minutes across every Hub.")

    def test_without_archetype_ref_no_rail_is_invented(self):
        sec = _event_like_section()
        sec.pop("archetypeRef")
        mapping = cfc._hero_mapping(sec)
        self.assertFalse([m for m in mapping if str(m["role"]).startswith("rail ")])


class NestedAssetWalks(unittest.TestCase):
    """_sanitize_assets/_declared_asset_names walk dict-copy repeatable sub-lists."""

    @classmethod
    def setUpClass(cls):
        cls.brand_dir = HUBSPOT.parent

    def test_nested_logo_assets_normalize_and_declare(self):
        comp = {"sections": [{
            "id": "hero", "slots": [
                {"name": "agenda", "contract": "logo-bar",
                 "copy": {"caption": "c", "logos": [
                     {"alt": "Marketing Hub",
                      "asset": "028-producticons-marketinghub-icon-orange.webp"},
                     {"alt": "Ghost", "asset": "not-a-real-file-xyz.png"},
                 ]}}]}]}
        out = cfc._sanitize_assets(comp, self.brand_dir)
        logos = out["sections"][0]["slots"][0]["copy"]["logos"]
        self.assertEqual(logos[0]["asset"],
                         {"src": "assets/028-producticons-marketinghub-icon-orange.webp"})
        self.assertIsNone(logos[1]["asset"])   # hallucinated file dropped
        names = cfc._declared_asset_names(out)
        self.assertIn("028-producticons-marketinghub-icon-orange.webp", names)
        self.assertNotIn("not-a-real-file-xyz.png", names)


class StackHeroRender(unittest.TestCase):
    """The rendered lane page proves the composer end: rail device present, both
    actions real, no SECTION_COPY ride-through, band on the plan's surface."""

    EVENT = (REPO / "runs" / "hubspot-v2" / "brand" / "compose" / "hero-archetypes"
             / "event" / "index.html")

    def test_event_page_renders_the_copy_first_plan(self):
        html = self.EVENT.read_text()
        self.assertIn('data-surface="surface/raised"', html)
        self.assertIn("cs-hero-rail", html)
        self.assertIn("Save my seat", html)
        self.assertIn("See the fall lineup", html)
        self.assertIn("Oct 8, 2026", html)
        # the homepage extraction's hero copy must NOT ride into the creative hero
        self.assertNotIn("Unite marketing, sales, and customer service", html)
        self.assertNotIn("HUBSPOT AGENTIC CUSTOMER PLATFORM", html)
        # rail marks are the brand's real files, unfiltered by the proof-wall treatment
        self.assertIn("producticons-marketinghub-icon-orange.webp", html)
        self.assertIn(".cs-hero-rail .cs-logo-strip .c-logo-img { filter: none", html)


class FootFormAndLinkRail(unittest.TestCase):
    """Stack-hero anatomy devices (fix6): a search-first hero's form + link slots map
    slot-faithfully (foot form / note-as-reason / quiet link rail) and never collide
    with the composer's core eyebrow/body/cta picks."""

    @staticmethod
    def _dev_like_section(**over):
        sec = {
            "id": "dev-hero", "useCase": "hero", "archetype": "stack",
            "surfaceIntent": "inverse", "archetypeRef": "hero-search-first",
            "slots": [
                {"name": "heading", "role": "display-title", "contract": "heading",
                 "copy": "Build on the platform."},
                {"name": "search", "role": "primary-control", "contract": "form",
                 "copy": {"fields": [{"label": "Search the docs",
                                      "placeholder": "Search the docs"}],
                          "submit": "Search",
                          "note": "Reference, guides, and changelogs."}},
                {"name": "popular", "role": "popular-links", "contract": "link",
                 "copy": [{"label": "CRM API", "variant": "arrow"}, {"label": "OAuth"}]},
            ],
        }
        sec.update(over)
        return sec

    def test_form_slot_maps_as_foot_form_with_note_attached(self):
        mapping = cfc._hero_mapping(self._dev_like_section())
        form = [m for m in mapping if str(m["role"]).startswith("foot form (")]
        note = [m for m in mapping if str(m["role"]).startswith("foot form note")]
        self.assertEqual(len(form), 1)
        self.assertEqual(form[0]["contract"], "form")
        self.assertEqual(form[0]["usage"]["placeholder"], "Search the docs")
        self.assertEqual(form[0]["usage"]["submit"], "Search")
        # fix7 punch 6: the note ATTACHES to its control — caption register below
        # the field (AS-14's stated reason is the section's own body copy, not
        # this meta line; fix6 had routed it as a paragraph ABOVE the field).
        self.assertEqual(len(note), 1)
        self.assertEqual(note[0]["contract"], "caption")

    def test_link_list_maps_as_quiet_rail_links(self):
        mapping = cfc._hero_mapping(self._dev_like_section())
        links = [m for m in mapping if str(m["role"]).startswith("rail link")]
        self.assertEqual([m["usage"]["label"] for m in links], ["CRM API", "OAuth"])
        # quiet register: never the page's committed accent (single-accent invariant),
        # and `text` rides along so the inline-props path (which honors accent) fires.
        for m in links:
            self.assertIs(m["usage"]["accent"], False)
            self.assertEqual(m["usage"]["text"], m["usage"]["label"])

    def test_without_archetype_ref_devices_never_map(self):
        sec = self._dev_like_section()
        sec.pop("archetypeRef")
        mapping = cfc._hero_mapping(sec)
        self.assertFalse([m for m in mapping
                          if str(m["role"]).startswith(("foot form", "rail "))])

    def test_composer_core_picks_exclude_device_fragments(self):
        """A device note renders ONCE (inside the form wrapper, attached BELOW the
        control — fix7 punch 6), never again as the hero body. Data-driven (pass2):
        when the lane's composition carries a form note it must render exactly once
        after the field; the current developer lane carries NONE (its note
        duplicated the quick-links rail — the AS-65 redundancy fix dropped it), so
        the wrapper renders bare and no floating meta line survives."""
        import html as H
        import json
        import re
        lane = REPO / "runs" / "hubspot-v2" / "brand" / "compose" / "hero-archetypes"
        comp = json.loads((lane / "developer" / "composition.json").read_text())
        note = next((s["copy"]["note"] for sec in comp["sections"]
                     for s in sec.get("slots", [])
                     if (s.get("contract") or "") == "form"
                     and isinstance(s.get("copy"), dict) and s["copy"].get("note")),
                    None)
        html_text = (lane / "developer" / "index.html").read_text()
        hero = re.search(r'<section class="cs-section cs-hero[^"]*">.*?</section>',
                         html_text, re.S).group(0)
        self.assertEqual(hero.count("cs-hero-form"), 1)
        self.assertIn("cs-hero-links", hero)
        if note is None:
            self.assertNotIn("foot form note", hero)
        else:
            note_esc = H.escape(note.strip(), quote=False).replace("'", "&#x27;")
            self.assertEqual(hero.count(note_esc), 1)
            # fix7: the note ATTACHES below its control, never above it
            self.assertGreater(hero.index(note_esc), hero.index("<input"))


class FormSplitHero(unittest.TestCase):
    """hero-form-split (fix6): a split hero binding a multi-field form slot stamps
    `_formFields`/`_formSplit` and composes the capture split — never the info-band
    that silently dropped the form."""

    @staticmethod
    def _demo_like_section(**over):
        sec = {
            "id": "hero-demo", "useCase": "hero", "archetype": "split",
            "surfaceIntent": "accent-wash", "archetypeRef": "hero-form-split",
            "knobs": {"formSide": "right", "formFrame": "panel"},
            "slots": [
                {"name": "kicker", "role": "eyebrow", "contract": "eyebrow",
                 "copy": "Book a demo"},
                {"name": "heading", "role": "display-title", "contract": "heading",
                 "copy": "See it work."},
                {"name": "support", "role": "body", "contract": "paragraph",
                 "copy": "Thirty minutes, tailored to your stack."},
                {"name": "see-points", "role": "value-list", "contract": "list",
                 "copy": ["Live pipeline", {"text": "One CRM"}]},
                {"name": "proof", "role": "proof", "contract": "stat",
                 "copy": {"value": "299,000+", "label": "customers"}},
                {"name": "demo-form", "role": "capture-form", "contract": "form",
                 "copy": {"header": {"heading": "Book your demo"},
                          "fields": [{"label": "First name"}, {"label": "Work email"}],
                          "submit": "Book my demo",
                          "note": "We'll email a scheduling link."}},
            ],
        }
        sec.update(over)
        return sec

    def test_split_hero_stamps_form_fields_and_form_split(self):
        layout = cfc.composition_to_layout(self._demo_like_section())
        ff = layout["_formFields"]
        self.assertEqual([f["label"] for f in ff["fields"]],
                         ["First name", "Work email"])
        # panel copy rides the stamp (heading/submit/note — fix6 additive keys)
        self.assertEqual(ff["heading"], "Book your demo")
        self.assertEqual(ff["submit"], "Book my demo")
        self.assertEqual(ff["note"], "We'll email a scheduling link.")
        # points accept bare strings AND the sanitizer's {"text": …} coercion;
        # supportKind rides the stamp since fix7 (empty here: no knob declared)
        self.assertEqual(layout["_formSplit"],
                         {"points": ["Live pipeline", "One CRM"], "side": "right",
                          "supportKind": ""})

    def test_formless_split_hero_stamps_nothing(self):
        sec = self._demo_like_section()
        sec["slots"] = [s for s in sec["slots"] if s["name"] != "demo-form"]
        layout = cfc.composition_to_layout(sec)
        self.assertNotIn("_formFields", layout)
        self.assertNotIn("_formSplit", layout)

    def test_demo_page_renders_the_capture_split(self):
        """Content-agnostic (pass2): the authored field labels/submit read from the
        lane's own composition so a regenerated lane keeps proving the device."""
        import json
        lane = REPO / "runs" / "hubspot-v2" / "brand" / "compose" / "hero-archetypes"
        html = (lane / "demo" / "index.html").read_text()
        comp = json.loads((lane / "demo" / "composition.json").read_text())
        form = next(s["copy"] for sec in comp["sections"]
                    for s in sec.get("slots", [])
                    if (s.get("contract") or "") == "form"
                    and isinstance(s.get("copy"), dict) and s["copy"].get("fields"))
        # the licensed nesting: white capture panel on the accent-wash band
        # (surface/panel allowedParents includes accent-wash; inverse does not)
        self.assertIn('data-surface="surface/accent-wash"', html)
        self.assertIn("cs-form-split-sec", html)
        self.assertIn("cs-signup-panel--plate", html)
        for f in form["fields"]:
            self.assertIn(str(f.get("label")), html)
        self.assertIn(str(form.get("submit") or "Submit"), html)

    def test_panel_nesting_license_backs_the_demo_reselection(self):
        doc = _hubspot_doc()
        rule = next(r for r in doc["surfaceGrammar"]["nesting"]
                    if r["child"] == "surface/panel")
        self.assertIn("surface/accent-wash", rule["allowedParents"])
        self.assertNotIn("surface/inverse", rule["allowedParents"])


class RunnerVariety(unittest.TestCase):
    """used_hero_surfaces reads sibling hero intents; order.txt is authoritative."""

    LANE = REPO / "runs" / "hubspot-v2" / "brand" / "compose" / "hero-archetypes"

    def test_used_hero_surfaces_reads_the_lane(self):
        """Content-agnostic (pass2 regenerated the lane's surface choices): the
        variety helper reads one hero surfaceIntent per sibling page and skips the
        requested stem — assert against the lane's OWN current compositions."""
        import json
        expected = []
        for p in sorted(self.LANE.glob("*/composition.json")):
            if p.parent.name == "event":
                continue
            sec = json.loads(p.read_text())["sections"][0]
            si = str(sec.get("surfaceIntent") or "").strip()
            if si:
                expected.append(si)
        used = runner.used_hero_surfaces(self.LANE, skip_stem="event")
        self.assertEqual(used, expected)
        self.assertEqual(len(used), 7)     # 8 heroes, event skipped
        with_event = runner.used_hero_surfaces(self.LANE)
        self.assertEqual(len(with_event), 8)

    def test_order_txt_is_authoritative_for_briefs(self):
        stems = [p.stem for p in runner.brief_order(self.LANE / "briefs", None)]
        self.assertNotIn("event-copy-first", stems)   # the plan doc never generates
        self.assertEqual(len(stems), 8)


if __name__ == "__main__":
    unittest.main()
