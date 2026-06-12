import unittest

from screenshot_to_template.surface_contract import (
    build_surface_component_contract,
    contract_audit_passed,
    render_surface_component_contract_for_prompt,
)


class SurfaceComponentContractTests(unittest.TestCase):
    def test_contract_extracts_nested_yaml_surfaces_and_children(self) -> None:
        section_yaml = """## 01-hero

schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  section_index: 1
  detected_label: Hero
section:
  id: hero
tree:
  id: root
  kind: section
  section_role: hero_header
  style:
    background_color_estimate: "#F8F1E7"
  children:
    - id: inner
      kind: layout
      layout_role: container
      children:
        - id: headline
          kind: text
          text_role: display
          text_scale: display_xl
          style:
            color_estimate: "#102030"
            font_size: 64px
            font_weight: 500
        - id: cta
          kind: control
          control_role: button
          style:
            background_color_estimate: "#102030"
            text_color: "#FFFFFF"
            border_radius: 999px
"""
        contract = build_surface_component_contract(section_yaml)

        self.assertTrue(contract_audit_passed(contract))
        hosts = contract["contracts"]["host_surfaces"]
        self.assertEqual(len(hosts), 1)
        self.assertGreaterEqual(len(hosts[0]["children"]), 3)
        self.assertTrue(contract["contracts"]["critical_pairings"])
        self.assertEqual(contract["audits"]["coverage"]["explicit_colors_observed"], 3)

    def test_prompt_render_strips_trace_ids(self) -> None:
        section_yaml = """schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  section_index: 1
tree:
  id: root
  kind: section
  section_role: feature
  children:
    - id: card
      kind: surface
      surface_role: card
      style:
        background_color_estimate: "#FFFFFF"
"""
        contract = build_surface_component_contract(section_yaml)
        rendered = render_surface_component_contract_for_prompt(contract)

        self.assertIn("surface_component_contract.v1", rendered)
        self.assertNotIn("trace_id", rendered)
        self.assertNotIn("section_01", rendered)

    def test_legacy_open_kinds_compile_but_do_not_pass_strict_auto_gate(self) -> None:
        section_yaml = """schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  section_index: 1
tree:
  id: root
  kind: section
  visibility: visible
  children:
    - id: old_panel
      kind: panel
      role: carousel_module_surface
      style:
        background_color_estimate: "#EFD0A1"
      children:
        - id: old_badge
          kind: badge
          role: item_status_label
          style:
            background_color_estimate: "#FFFFFF"
"""
        contract = build_surface_component_contract(section_yaml)

        self.assertFalse(contract_audit_passed(contract))
        self.assertGreater(contract["audits"]["coverage"]["child_recipe_count"], 0)
        self.assertFalse(contract["audits"]["validity"]["raw_schema_uses_closed_kind_enum"])


if __name__ == "__main__":
    unittest.main()
