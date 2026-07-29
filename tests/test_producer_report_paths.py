"""Every producer that records a path records it the way the repo sees it.

`tools/track_studio_subset.py` refuses to track a text artifact containing this
checkout's absolute path — the repo is public and the path embeds a username. So
an artifact that writes an absolute path does not merely look untidy: it drops
itself, and the Studio tab that reads it, out of the committed subset. 237 files
across eleven projects were being held back for exactly this.

The fix is at each producer, via `screenshot_to_template.repo_paths.report_path`.
These tests hold each producer to the result rather than to the call: a temporary
directory stands in as "the repo", the producer runs against a fixture inside it,
and the recorded field must come out relative. `leaks_local_path()` — the
tracker's own gate — is then applied to the bytes the producer wrote, so a
regression fails here for the same reason it would fail the tracker.

The producers that cannot run without a browser (`spacing_audit`,
`signature_audit`, `css_fidelity`) keep this suite browser-free by being checked
structurally instead: their path fields must not be built with a bare `str()`.
"""

import ast
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
for extra in ("brand_pipeline", "tools/extract"):
    sys.path.insert(0, str(REPO_ROOT / extra))
sys.path.insert(0, str(REPO_ROOT))

from screenshot_to_template import repo_paths  # noqa: E402
from screenshot_to_template import site_assets, source_colors, source_style_ledger  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "tools"))
import track_studio_subset as tracker  # noqa: E402

import conversion_audit  # noqa: E402
import curate_assets  # noqa: E402
import interaction_audit  # noqa: E402
import mine_dom  # noqa: E402
import run_brand_extraction  # noqa: E402
import section_rules_audit  # noqa: E402
import tokens_css  # noqa: E402
import validate_brand_evidence  # noqa: E402
import voice_audit  # noqa: E402


class ProducerCase(unittest.TestCase):
    """A temp dir standing in as the repo, so a fixture can be 'inside' it.

    `report_path()` reads `repo_paths.REPO_ROOT` at call time and every producer
    imports the function, so redirecting that one global redirects all of them —
    no producer needs a test hook of its own.
    """

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.repo = Path(self._tmp.name).resolve()
        self._real_root = repo_paths.REPO_ROOT
        repo_paths.REPO_ROOT = self.repo
        self.brand_dir = self.repo / "runs" / "acme" / "brand"
        self.brand_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        repo_paths.REPO_ROOT = self._real_root
        self._tmp.cleanup()

    def lane(self, name: str = "compose/homepage") -> Path:
        """A lane index.html inside the stand-in repo."""
        html = self.brand_dir / name / "index.html"
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text("<html><body><h1>Acme</h1></body></html>", encoding="utf-8")
        return html

    def assertRecordedRelative(self, value, expected: str) -> None:
        self.assertEqual(value, expected)
        self.assertFalse(Path(value).is_absolute(), value)

    def assertNoLeakOnDisk(self, *paths: Path) -> None:
        """The tracker's own gate, applied to what the producer just wrote.

        `leaks_local_path()` compares against the REAL checkout, so the fixture's
        stand-in repo is pointed at the checkout for the duration of the check —
        otherwise the gate would be looking for a prefix that cannot appear.
        """
        real_markers = tracker.LOCAL_PATH_MARKERS
        tracker.LOCAL_PATH_MARKERS = (str(self.repo),)
        try:
            for path in paths:
                self.assertTrue(path.is_file(), f"{path} was not written")
                self.assertFalse(
                    tracker.leaks_local_path(path),
                    f"{path.name} embeds the checkout path — the tracker would hold it back",
                )
        finally:
            tracker.LOCAL_PATH_MARKERS = real_markers


class VoiceAuditTests(ProducerCase):
    """`brand/compose/**/battery/voice/report.json` — brandDir + lanes[].html."""

    def test_brand_dir_and_lane_html_are_repo_relative(self) -> None:
        (self.brand_dir / "voice-facts.yaml").write_text(
            "schema: voice-facts.v1\n", encoding="utf-8"
        )
        out = self.repo / "out"
        report = voice_audit.run_audit([self.lane()], self.brand_dir, out)
        self.assertRecordedRelative(report["brandDir"], "runs/acme/brand")
        self.assertRecordedRelative(
            report["lanes"][0]["html"], "runs/acme/brand/compose/homepage/index.html"
        )
        self.assertNoLeakOnDisk(out / "report.json")


class SectionRulesAuditTests(ProducerCase):
    """`battery/section-rules/report.{json,md}` — brandDir + lanes[].html."""

    def test_brand_dir_and_lane_html_are_repo_relative(self) -> None:
        out = self.repo / "out"
        report = section_rules_audit.run_audit(
            [self.lane()], self.brand_dir, out, static_only=True
        )
        self.assertRecordedRelative(report["brandDir"], "runs/acme/brand")
        self.assertRecordedRelative(
            report["lanes"][0]["html"], "runs/acme/brand/compose/homepage/index.html"
        )
        self.assertNoLeakOnDisk(out / "report.json", out / "report.md")


class ConversionAuditTests(ProducerCase):
    """`battery/conversion/report.{json,md}` — lanes[].lane."""

    def test_lane_is_repo_relative(self) -> None:
        lane_dir = self.lane().parent
        entry = conversion_audit.audit_lane(lane_dir, conversion_audit.load_contracts())
        self.assertRecordedRelative(entry["lane"], "runs/acme/brand/compose/homepage")


class InteractionAuditTests(ProducerCase):
    """`battery/interaction/report.{json,md}` — lanes[].path."""

    def test_lane_path_is_repo_relative(self) -> None:
        out = self.repo / "out"
        html = self.lane()
        with contextlib.redirect_stdout(io.StringIO()):
            interaction_audit.main([str(html), "--out", str(out), "--static-only"])
        payload = json.loads((out / "report.json").read_text())
        self.assertRecordedRelative(
            payload["lanes"][0]["path"], "runs/acme/brand/compose/homepage/index.html"
        )
        self.assertNoLeakOnDisk(out / "report.json", out / "report.md")


class TokensCssTests(ProducerCase):
    """The token generator's fail-loud message names the brand.yaml to fix.

    That message is copied verbatim into `brand/author-stage-status.json`,
    `brand/author-report.json` and `brand/manifest.json`, so the path it carries
    decides whether the Author report tab travels.
    """

    def test_missing_token_error_names_brand_yaml_repo_relative(self) -> None:
        brand_yaml = self.brand_dir / "brand.yaml"
        brand_yaml.write_text("brand:\n  name: Acme\n", encoding="utf-8")
        with self.assertRaises(tokens_css.TokenGenerationError) as caught:
            tokens_css.build_page_tokens({"brand": {"name": "Acme"}},
                                         brand_yaml_path=brand_yaml)
        message = str(caught.exception)
        self.assertIn("(source: runs/acme/brand/brand.yaml)", message)
        self.assertNotIn(str(self.repo), message)


class MineDomTests(ProducerCase):
    """`brand/evidence/dom-sections.json` — source."""

    def test_source_is_repo_relative(self) -> None:
        capture = self.repo / "screenshots" / "acme"
        capture.mkdir(parents=True)
        html = capture / "acme.html"
        html.write_text("<html><body><section><h2>Hi</h2></section></body></html>",
                        encoding="utf-8")
        self.assertRecordedRelative(mine_dom.mine(html)["source"],
                                    "screenshots/acme/acme.html")


class CurateAssetsTests(ProducerCase):
    """`brand/assets-manifest.json` — entries[].source."""

    def test_entry_source_is_repo_relative(self) -> None:
        src = self.repo / "screenshots" / "acme" / "acme_files" / "logo.svg"
        src.parent.mkdir(parents=True)
        src.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        dest = self.brand_dir / "assets" / "logo.svg"
        dest.parent.mkdir(parents=True)
        entries: list[dict] = []
        curate_assets._copy(src, dest, True, entries, "capture", "logo")
        self.assertRecordedRelative(entries[0]["source"],
                                    "screenshots/acme/acme_files/logo.svg")


class SourceColorsTests(ProducerCase):
    """`<lane>/single/source-colors.{json,md}` — source_html.

    `source-style-ledger.yaml` copies this same field into `html_path`, and
    reads it back to re-parse the source, so the round trip is checked too.
    """

    def _capture(self) -> Path:
        html = self.repo / "screenshots" / "acme" / "acme.html"
        html.parent.mkdir(parents=True)
        html.write_text(
            "<html><head><style>:root{--brand:#0a5;}body{color:#0a5}</style></head>"
            "<body><h1>Acme</h1></body></html>",
            encoding="utf-8",
        )
        return html

    def test_source_html_is_repo_relative(self) -> None:
        extracted = source_colors.extract_source_colors(self._capture())
        self.assertRecordedRelative(extracted["source_html"], "screenshots/acme/acme.html")

    def test_the_ledger_reads_the_relative_value_back_from_any_cwd(self) -> None:
        extracted = source_colors.extract_source_colors(self._capture())
        declarations = source_style_ledger.extract_source_style_declarations(extracted)
        self.assertTrue(declarations, "a repo-relative source_html must still resolve")


class SiteAssetsTests(ProducerCase):
    """`<lane>/single/<site>.assets.json` — html."""

    def test_html_is_repo_relative(self) -> None:
        single = self.repo / "runs" / "acme" / "acme" / "single"
        single.mkdir(parents=True)
        manifest = single / "site.assets.json"
        site_assets._write_asset_manifest(
            manifest,
            status="ok",
            model_name="none",
            html_path=single / "site.html",
            replacements=[],
            manifest_candidates=[],
        )
        payload = json.loads(manifest.read_text())
        self.assertRecordedRelative(payload["html"], "runs/acme/acme/single/site.html")
        self.assertNoLeakOnDisk(manifest)


class BrandExtractionLogTests(ProducerCase):
    """`validate-final.log` — the captured console transcript of the run.

    Three lines carried the checkout path: the `Capture:` header, the echoed
    stage argv, and the validator's own verdict line.
    """

    def test_echoed_stage_argv_names_repo_paths_relatively(self) -> None:
        echoed = run_brand_extraction.echoed_argv(
            ["--brand-dir", str(self.brand_dir), "--min-logo-assets", "3"]
        )
        self.assertEqual(echoed, "--brand-dir runs/acme/brand --min-logo-assets 3")

    def test_a_non_path_argument_is_left_alone(self) -> None:
        self.assertEqual(
            run_brand_extraction.echoed_argv(["--viewport", "1440x900", "--js"]),
            "--viewport 1440x900 --js",
        )

    def test_validator_verdict_and_errors_name_the_brand_dir_relatively(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            validate_brand_evidence.main(["--brand-dir", str(self.brand_dir)])
        out = buffer.getvalue()
        self.assertIn("[FAIL] runs/acme/brand:", out)
        self.assertIn("runs/acme/brand/brand.yaml missing", out)
        self.assertNotIn(str(self.repo), out)


# ── the browser-bound producers ───────────────────────────────────────────────
# These record their path fields inside a function that drives Chromium, so they
# are held to the shape of the write instead of to its result — which keeps this
# suite runnable on a clone with no browser installed. `str(<path>)` is the exact
# regression being guarded: it is what every one of these fields used to be.
_STRUCTURAL_CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("brand_pipeline/spacing_audit.py", ("brandDir", "html")),
    ("brand_pipeline/signature_audit.py", ("brandDir", "html", "lane")),
    ("brand_pipeline/css_fidelity.py", ("replicaIndex", "joinedEvidence", "source")),
    ("brand_pipeline/section_rules_audit.py", ("brandDir", "html", "lane")),
    ("brand_pipeline/voice_audit.py", ("brandDir", "html", "lane")),
    ("brand_pipeline/conversion_audit.py", ("lane",)),
)


def _str_calls_for_key(source: str, key: str) -> list[int]:
    """Line numbers where `{"<key>": str(...)}` is written in `source`."""
    lines: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Dict):
            continue
        for k, value in zip(node.keys, node.values):
            if not (isinstance(k, ast.Constant) and k.value == key):
                continue
            for candidate in (value.body, value.orelse) if isinstance(value, ast.IfExp) else (value,):
                if (isinstance(candidate, ast.Call)
                        and isinstance(candidate.func, ast.Name)
                        and candidate.func.id == "str"):
                    lines.append(candidate.lineno)
    return lines


class PathFieldsAreNotBuiltWithStrTests(unittest.TestCase):
    def test_no_producer_records_a_path_field_with_str(self) -> None:
        for rel, keys in _STRUCTURAL_CHECKS:
            source = (REPO_ROOT / rel).read_text(encoding="utf-8")
            for key in keys:
                with self.subTest(module=rel, field=key):
                    self.assertEqual(
                        _str_calls_for_key(source, key), [],
                        f"{rel} writes {key!r} with str() — route it through report_path()",
                    )

    def test_the_guard_would_catch_the_regression_it_guards(self) -> None:
        self.assertEqual(
            _str_calls_for_key('report = {"brandDir": str(brand_dir)}', "brandDir"), [1]
        )
        self.assertEqual(
            _str_calls_for_key('report = {"brandDir": report_path(brand_dir)}', "brandDir"),
            [],
        )


# ── the on-brand gate's markdown prose ────────────────────────────────────────
# `onbrand-report.md` carried the checkout path in three sentences rather than in
# a field: the active-STYLE-layer line and the two "Next steps" commands. Prose is
# rendered from a brand doc plus a live render, so this is held to the shape of the
# interpolation — a path may reach an f-string only through `report_path()` (or
# through something like `Path(p).name`, which cannot carry a directory).
_BARE_PATH_INTERPOLATIONS = ("render_dir", "style.source_path")


def _interpolated_names(source: str) -> set[str]:
    """Every expression an f-string in `source` interpolates *bare*, as written."""
    bare: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.JoinedStr):
            continue
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                value = part.value
                if isinstance(value, (ast.Name, ast.Attribute)):
                    bare.add(ast.unparse(value))
    return bare


#: `re.<name>` and how many positional arguments precede its count/maxsplit slot.
_RE_COUNT_ARITY = {"split": 2, "sub": 3, "subn": 3}


def _positional_maxsplit_lines(source: str) -> list[int]:
    """Line numbers of `re.split(pattern, s, <n>)` — a DeprecationWarning in 3.13+."""
    lines: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "re"
                and len(node.args) > _RE_COUNT_ARITY.get(node.func.attr, len(node.args))):
            lines.append(node.lineno)
    return lines


class OnBrandReportProseTests(unittest.TestCase):
    def test_the_gate_never_interpolates_a_path_into_prose_bare(self) -> None:
        source = (REPO_ROOT / "brand_pipeline/onbrand_check.py").read_text(encoding="utf-8")
        interpolated = _interpolated_names(source)
        for name in _BARE_PATH_INTERPOLATIONS:
            with self.subTest(expression=name):
                self.assertNotIn(
                    name, interpolated,
                    f"onbrand_check.py writes `{name}` into report prose bare — "
                    "route it through report_path()",
                )

    def test_the_guard_would_catch_the_regression_it_guards(self) -> None:
        self.assertIn("render_dir", _interpolated_names('w(f"- Re-generate: {render_dir}")'))
        self.assertNotIn(
            "render_dir", _interpolated_names('w(f"- Re-generate: {report_path(render_dir)}")')
        )

    def test_no_producer_warns_with_a_positional_maxsplit(self) -> None:
        """A DeprecationWarning prints the module's own absolute `__file__`.

        That is how the checkout path reached `onbrand-console.txt` and the battery
        `onbrand.log` — no field on the artifact was at fault, the interpreter's
        warning was. Keyword `maxsplit=`/`count=` keeps the warning unraised.
        """
        for rel, _keys in _STRUCTURAL_CHECKS + (("brand_pipeline/onbrand_check.py", ()),):
            with self.subTest(module=rel):
                source = (REPO_ROOT / rel).read_text(encoding="utf-8")
                self.assertEqual(
                    _positional_maxsplit_lines(source), [],
                    f"{rel} passes maxsplit/count positionally — pass it by keyword so "
                    "no DeprecationWarning prints this checkout's path",
                )

    def test_the_maxsplit_guard_would_catch_the_regression_it_guards(self) -> None:
        self.assertEqual(_positional_maxsplit_lines('re.split(r"[;{}]", val, 1)'), [1])
        self.assertEqual(_positional_maxsplit_lines('re.split(r"[;{}]", val, maxsplit=1)'), [])


if __name__ == "__main__":
    unittest.main()
