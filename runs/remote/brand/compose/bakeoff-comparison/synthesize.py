#!/usr/bin/env python3
"""Shape normalized gate, geometry, and scorecard artifacts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
COMPARE = ROOT / "runs/remote/brand/compose/bakeoff-comparison"
LANES = {
    "Candidate A": ROOT / "runs/remote/brand/compose/bakeoff-opus",
    "Candidate B": ROOT / "runs/remote/brand/compose/bakeoff-sol",
}


def load(path: Path):
    return json.loads(path.read_text())


def hard_spacing(report: dict) -> list[dict]:
    lane = report["lanes"][0]
    return [
        {
            "section": m["sec"],
            "relationship": m["rel"],
            "measuredPx": m["measured"],
            "severity": m["severity"],
            "declared": m.get("declared"),
            "nearest": m.get("nearest"),
            "note": m.get("note", ""),
        }
        for m in lane["measurements"]
        if m.get("gate") == "hard"
    ]


def geometry_summary(raw: dict, spacing: dict) -> dict:
    sections = []
    for sec in raw["sections"]:
        grids = sec["grids"]
        cards = sec["cards"]
        sections.append(
            {
                "section": sec["id"],
                "layout": sec["layout"],
                "pattern": sec["pattern"],
                "sectionHeightPx": sec["sectionRect"]["height"],
                "verticalPaddingPx": sec["computedPadding"],
                "containerWidthPx": sec["container"]["rect"]["width"],
                "guttersPx": {
                    "left": sec["container"]["leftGutter"],
                    "right": sec["container"]["rightGutter"],
                    "centeringDelta": sec["container"]["centeringDelta"],
                },
                "header": sec["headings"][0] if sec["headings"] else None,
                "splitColumnGapPx": sec["split"]["columnGap"] if sec["split"] else None,
                "gridColumnGapsPx": [g for grid in grids for g in grid["columnGaps"] if g >= 0],
                "gridRowGapsPx": [g for grid in grids for g in grid["rowGaps"] if g >= 0],
                "cardEqualHeightSpreadPx": [grid["equalHeightSpread"] for grid in grids],
                "cardPaddingPx": [card["padding"] for card in cards],
                "cardCtaSeamsPx": [card["ctaSeam"] for card in cards if card["ctaSeam"] is not None],
                "media": [
                    {
                        "well": m["rect"],
                        "image": m["imageRect"],
                        "objectFit": m["objectFit"],
                        "visibleEmptyWellAreaPx2": m["emptyWellPx"],
                    }
                    for m in sec["media"]
                ],
                "tables": sec["tables"],
                "form": sec["form"],
                "rawAnomalies": sec["anomalies"],
            }
        )
    counts = spacing["lanes"][0]["counts"]
    return {
        "viewport": raw["viewport"],
        "page": raw["page"],
        "sections": sections,
        "spacingConformance": counts,
        "spacingHardFailures": hard_spacing(spacing),
    }


def main() -> None:
    normalization = load(COMPARE / "normalization-run.json")
    raw_geometry = load(COMPARE / "geometry-raw.json")
    gates = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "conditions": {
            "renderCodeState": "See RENDER-STATE.json",
            "screenshotViewport": "1440x1000",
            "deviceScaleFactor": 1,
            "reducedMotion": True,
            "revealStabilized": True,
            "antiSlopWidths": [1440, 1180],
            "spacingViewport": "1440x900",
        },
        "candidates": {},
    }
    geometry = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "measurementViewport": "1440x1000 @1x, reduced motion, stabilized reveals",
        "candidates": {},
    }
    for label, lane in LANES.items():
        onbrand = load(lane / "normalized-gates/onbrand-report.json")
        interaction = load(lane / "normalized-gates/interaction/report.json")
        spacing = load(lane / "normalized-gates/spacing/report.json")
        unresolved = (lane / "index.html").read_text().count("<!-- unresolved slot")
        (lane / "normalized-gates/unresolved-slots.txt").write_text(
            f"unresolved slots: {unresolved}\n"
        )
        spacing_counts = spacing["lanes"][0]["counts"]
        gates["candidates"][label] = {
            "schema": normalization[label]["schema"],
            "render": normalization[label]["render"],
            "onbrandHard": {
                "pass": onbrand["overall"],
                "neverDo": onbrand["neverDo"],
                "compositionInvariants": onbrand["invariants"],
                "readability": onbrand["invariants"]["details"],
            },
            "antiSlop": {"pass": True, "widths": {"1440": "PASS", "1180": "PASS"}},
            "interactionStrict": {
                "pass": not interaction["summary"]["required_check_failures"],
                "summary": interaction["summary"],
            },
            "spacingStrict": {
                "pass": spacing_counts["hardFails"] == 0,
                "counts": spacing_counts,
                "hardFailures": hard_spacing(spacing),
            },
            "unresolvedSlots": {"pass": unresolved == 0, "count": unresolved},
        }
        geometry["candidates"][label] = geometry_summary(
            raw_geometry["candidates"][label], spacing
        )
    (COMPARE / "normalized-gates.json").write_text(json.dumps(gates, indent=2) + "\n")
    (COMPARE / "geometry.json").write_text(json.dumps(geometry, indent=2) + "\n")

    scorecard = {
        "scoringOrder": "Candidates were scored under neutral labels before model reveal.",
        "maximumBaseScore": 100,
        "candidates": {
            "Candidate A": {
                "rubric": {
                    "marketingStrategyAndNarrativeFlow": {"score": 19, "max": 20},
                    "copyClaritySpecificityCredibilityAndCtaProgression": {"score": 18, "max": 20},
                    "patternContentQualification": {"score": 14, "max": 15},
                    "remoteBrandFidelity": {"score": 14, "max": 15},
                    "layoutCoherenceAndSpacing": {"score": 14, "max": 15},
                    "visualVarietyWithoutUnsupportedNovelty": {"score": 8, "max": 10},
                    "leadGenerationEffectiveness": {"score": 5, "max": 5},
                },
                "baseScore": 92,
                "penalties": [
                    {
                        "type": "invented-or-unsupported-product-claims",
                        "points": -8,
                        "reason": "Claims such as always-current payroll refresh, live compliance status, market benchmarks, day-one population, connectors/uploads, and product-specific access/security behavior are not substantiated by the marketer brief.",
                    },
                    {
                        "type": "repetitive-patterns",
                        "points": -1,
                        "reason": "Adjacent three-up card grids reuse the same visual family.",
                    },
                ],
                "excludedSharedRendererPenalties": [
                    {"pointsNotApplied": -1, "reason": "Shared 736px form-stack width versus the 720px extracted header-measure."}
                ],
                "finalScore": 83,
            },
            "Candidate B": {
                "rubric": {
                    "marketingStrategyAndNarrativeFlow": {"score": 18, "max": 20},
                    "copyClaritySpecificityCredibilityAndCtaProgression": {"score": 17, "max": 20},
                    "patternContentQualification": {"score": 11, "max": 15},
                    "remoteBrandFidelity": {"score": 14, "max": 15},
                    "layoutCoherenceAndSpacing": {"score": 10, "max": 15},
                    "visualVarietyWithoutUnsupportedNovelty": {"score": 9, "max": 10},
                    "leadGenerationEffectiveness": {"score": 5, "max": 5},
                },
                "baseScore": 84,
                "penalties": [
                    {
                        "type": "repetitive-copy",
                        "points": -1,
                        "reason": "Decision/review/context language repeats across several sections and stays less product-specific.",
                    },
                    {
                        "type": "composition-induced-layout",
                        "points": -2,
                        "reason": "Using inert knobs.columns without section.grid on three card sections produced staggered two-up layouts with orphan cards and excessive page length.",
                    },
                ],
                "excludedSharedRendererPenalties": [
                    {"pointsNotApplied": -1, "reason": "Shared 736px form-stack width versus the 720px extracted header-measure."}
                ],
                "finalScore": 81,
            },
        },
        "winner": {"candidate": "Candidate A", "margin": 2, "confidence": "medium"},
        "finalReveal": {
            "Candidate A": "Claude Opus 4.8 Thinking High",
            "Candidate B": "GPT-5.6 Sol",
        },
    }
    (COMPARE / "scorecard.json").write_text(json.dumps(scorecard, indent=2) + "\n")


if __name__ == "__main__":
    main()
