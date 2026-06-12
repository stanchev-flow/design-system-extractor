import tempfile
import unittest
from pathlib import Path

from run_pipeline import coerce_design_system_markdown_document, write_design_system_artifacts


class DesignSystemArtifactTests(unittest.TestCase):
    def test_pure_yaml_design_system_is_saved_as_markdown_front_matter(self) -> None:
        content = """schema_version: design_system_yaml.v1
type: design_system
metadata:
  name: test_system
  description: A compact test system.
tokens:
  color:
    surface:
      primary: "#FFFFFF"
surfaces:
  primary:
    value: "#FFFFFF"
    role: page_canvas
    text:
      default: "#111111"
components:
  button_primary:
    kind: button
    variants:
      on_primary:
        surface: primary
imagery:
  illustrations:
    observed: true
    creativeDirection: sparse line art
rules:
  color:
    - Keep primary surfaces quiet.
"""
        rendered = coerce_design_system_markdown_document(content)

        self.assertTrue(rendered.startswith("---\n"))
        self.assertIn("type: design_system", rendered)
        self.assertIn("## Surface System", rendered)
        self.assertIn("## Components", rendered)
        self.assertIn("## Imagery", rendered)
        self.assertIn("## Rules", rendered)

    def test_write_design_system_artifacts_removes_stale_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mode_dir = Path(temp_dir)
            stale_yaml = mode_dir / "design-system.yaml"
            stale_yaml.write_text("type: design_system\n")

            path = write_design_system_artifacts(
                mode_dir,
                "schema_version: design_system_yaml.v1\ntype: design_system\nmetadata:\n  name: test\n",
            )

            self.assertEqual(path, mode_dir / "design-system.md")
            self.assertTrue(path.exists())
            self.assertFalse(stale_yaml.exists())


if __name__ == "__main__":
    unittest.main()
