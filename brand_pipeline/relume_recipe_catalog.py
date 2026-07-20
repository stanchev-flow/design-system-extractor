#!/usr/bin/env python3
"""Compile Relume component metadata into reusable section-recipe families.

The checked-in inventory contains metadata returned by the authenticated Relume MCP,
not vendored component source.  This compiler deliberately removes presentation and
copy details, folds mirrored layouts into one family, and records ingredient/media
differences as variant axes instead of materialising every combination.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = REPO_ROOT / "brand_pipeline" / "contracts" / "section-recipes"
INVENTORY_DIR = CATALOG_DIR / "inventory"
GENERATED_CATALOG = CATALOG_DIR / "catalog.generated.yaml"
STRUCTURAL_CATALOG = CATALOG_DIR / "catalog.structural.yaml"
GENERATED_COVERAGE_JSON = CATALOG_DIR / "coverage.generated.json"
GENERATED_COVERAGE_MD = CATALOG_DIR / "coverage.generated.md"
RESPONSIVE_EVIDENCE = CATALOG_DIR / "responsive-evidence.yaml"

SCHEMA_VERSION = "section-recipes.v1"
STRUCTURAL_SCHEMA_VERSION = "section-recipes.structural.v1"
INVENTORY_SCHEMA_VERSION = "relume-inventory.v1"
RESPONSIVE_SCHEMA_VERSION = "relume-responsive-evidence.v1"

_FORBIDDEN_PROMPT_KEYS = re.compile(
    r"(?:color|font|typography|typeSize|lineHeight|tracking|padding|margin|gap|radius|"
    r"border|shadow|className|sourceClass|preview|url|query)$",
    re.IGNORECASE,
)
_LITERAL_CSS_RE = re.compile(
    r"(?:#[0-9a-f]{3,8}\b|(?:^|[^a-z])[-+]?\d*\.?\d+(?:px|rem|em|vw|vh|dvh|svh|lvh|%)"
    r"(?=[^a-z0-9]|$)|\[[^\]]*\]|\d*\.?\d+fr\b|max-content|"
    r"calc\s*\(|@media|max-width\s*:|min-width\s*:|https?://)",
    re.IGNORECASE,
)
_PROMPT_RECIPE_KEYS = {
    "id", "sectionType", "builderUseCase", "structure", "slots", "variantAxes",
    "responsive", "provenance",
}
_PROMPT_AXES = {
    "columns", "textAlign", "mediaSide", "mediaMode", "interaction", "ingredients",
    "logoPosition", "menuPosition",
}
_PROMPT_RULE_AXES = {
    "display", "columns", "flexDirection", "order", "overflow", "mediaAspect",
    "mediaCrop", "itemBasis", "sticky", "interaction", "carouselInteraction",
    "dialogInteraction", "conditionalMotion", "responsiveInvariant", "breakpointTier",
    "containerWidth", "scrollStage", "viewportHeight",
}


def _semantic_rule(rule: dict) -> dict | None:
    """Project one raw responsive observation into topology-only semantics."""
    axis = str(rule.get("axis") or "")
    values = " ".join(str(rule.get(key) or "") for key in ("base", "value", "atLg"))
    lowered = values.lower().replace(" ", "")
    if axis == "breakpointQuery":
        return {"axis": "breakpointTier", "base": "mobile", "at": "lg", "value": "desktop"}
    if "738px" in lowered or "940px" in lowered:
        return {
            "axis": "containerWidth", "base": "medium", "at": "lg", "value": "large"
        }
    if "400vh" in lowered:
        return {"axis": "scrollStage", "base": "extended", "value": "extended"}
    if "200vh" in lowered:
        return {"axis": "scrollStage", "base": "long", "value": "long"}
    if "calc(100vh" in lowered:
        return {
            "axis": "viewportHeight",
            "base": "viewport-minus-header",
            "value": "viewport-minus-header",
        }
    if axis not in _PROMPT_RULE_AXES:
        return None
    projected = {"axis": axis}
    for key in ("base", "at", "value", "atSm", "atMd", "atLg", "atXl", "at2Xl"):
        if key not in rule:
            continue
        value = rule[key]
        raw_value = str(value)
        if _LITERAL_CSS_RE.search(raw_value):
            if axis == "mediaAspect" and raw_value.startswith("["):
                fraction = raw_value.strip("[]")
                value = "portrait" if fraction in {"5/6", "10/12"} else "landscape"
            elif axis == "columns" and raw_value.startswith("["):
                tracks = raw_value.strip("[]").split("_")
                value = (
                    "content-plus-auto" if "max-content" in raw_value
                    else f"asymmetric-{len(tracks)}-column"
                )
            elif axis == "itemBasis":
                value = "partial-track"
            else:
                continue
        projected[key] = value
    if "base" not in projected:
        return None
    return projected


def structural_projection(doc: dict) -> dict:
    """Create the strict, prompt-facing projection; raw evidence remains untouched."""
    recipes = []
    for raw in doc.get("recipes") or []:
        axes = {
            key: value for key, value in (raw.get("variantAxes") or {}).items()
            if key in _PROMPT_AXES
        }
        rules = [
            projected for rule in ((raw.get("responsive") or {}).get("rules") or [])
            if isinstance(rule, dict) and (projected := _semantic_rule(rule)) is not None
        ]
        recipe = {
            "id": raw.get("id"),
            "sectionType": raw.get("sectionType"),
            "builderUseCase": raw.get("builderUseCase"),
            "structure": raw.get("structure") or {},
            "slots": raw.get("slots") or {},
            "variantAxes": axes,
            "responsive": {
                "breakpointModel": "semantic-mobile-first",
                "orientationIsVariant": bool(
                    (raw.get("responsive") or {}).get("orientationIsVariant")
                ),
                "rules": rules,
            },
            "provenance": {"sourceRecipeId": raw.get("id")},
        }
        unknown = set(recipe) - _PROMPT_RECIPE_KEYS
        if unknown:
            raise ValueError(f"{raw.get('id')}: prompt recipe has unknown keys {sorted(unknown)}")
        recipes.append(recipe)
    projected = {
        "schemaVersion": STRUCTURAL_SCHEMA_VERSION,
        "sourceCatalogSchemaVersion": doc.get("schemaVersion"),
        "policy": "structure-only-fallback",
        "recipes": recipes,
    }
    assert_prompt_safe(projected)
    return projected


def scan_prompt_values(value: object, path: str = "$") -> list[str]:
    """Return forbidden prompt-facing keys and literal CSS/source values."""
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _FORBIDDEN_PROMPT_KEYS.search(str(key)):
                errors.append(f"{child_path}: forbidden visual/source key")
            errors.extend(scan_prompt_values(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(scan_prompt_values(child, f"{path}[{index}]"))
    elif isinstance(value, str) and _LITERAL_CSS_RE.search(value):
        errors.append(f"{path}: forbidden literal {value!r}")
    return errors


def assert_prompt_safe(value: object) -> None:
    errors = scan_prompt_values(value)
    if errors:
        raise ValueError("unsafe Relume prompt projection:\n" + "\n".join(errors[:20]))


def write_structural_catalog(doc: dict, output: Path = STRUCTURAL_CATALOG) -> Path:
    projected = structural_projection(doc)
    output.write_text(yaml.safe_dump(projected, sort_keys=False, width=110))
    return output

# Rich section types remain distinct even when the current composition runtime has to
# retrieve them through a broader layout_library use-case.
CATEGORY_TAXONOMY = {
    "navbars": ("navigation", None),
    "footers": ("footer", "footer"),
    "hero-header-sections": ("hero", "hero"),
    "header-sections": ("header", "hero"),
    "feature-sections": ("feature", "features"),
    "cta-sections": ("cta", "cta"),
    "contact-sections": ("contact", "cta"),
    "pricing-sections": ("pricing", "pricing"),
    "faq-sections": ("faq", "faq"),
    "testimonial-sections": ("testimonial", "testimonial"),
    "logo-sections": ("logo-wall", "logos"),
    "team-sections": ("team", "about"),
    "blog-header-sections": ("content-header", "hero"),
    "blog-sections": ("content-feed", "gallery"),
    "blog-post-headers": ("content-detail-header", "hero"),
    "career-sections": ("careers", "about"),
    "gallery-sections": ("gallery", "gallery"),
    "contact-modals": ("contact-modal", "cta"),
    "banners": ("banner", "cta"),
    "portfolio-headers": ("portfolio-header", "hero"),
    "portfolio-sections": ("portfolio", "gallery"),
    "event-headers": ("event-header", "hero"),
    "event-item-headers": ("event-detail-header", "hero"),
    "event-sections": ("events-feed", "gallery"),
    "product-list-sections": ("product-list", "gallery"),
    "multi-step-forms": ("multi-step-form", "cta"),
    "product-headers": ("product-header", "hero"),
    "stats-sections": ("stats", "features"),
    "category-filters": ("category-filter", "gallery"),
    "long-form-content-sections": ("long-form-content", "about"),
    "loaders": ("loader", None),
    "application-shells": ("application-shell", None),
    "sidebars": ("sidebar", None),
    "topbars": ("topbar", None),
    "page-headers": ("app-page-header", "hero"),
    "section-headers": ("section-header", "features"),
    "card-headers": ("card-header", "features"),
    "signup-login-pages": ("authentication", "cta"),
    "onboarding-forms": ("onboarding", "cta"),
    "signup-login-modals": ("authentication-modal", "cta"),
    "tables": ("table", "features"),
    "stacked-lists": ("stacked-list", "features"),
    "grid-lists": ("grid-list", "gallery"),
    "stat-cards": ("stat-cards", "features"),
    "forms": ("form", "cta"),
    "description-lists": ("description-list", "features"),
    "comparison-sections": ("comparison", "pricing"),
    "cookie-consent": ("cookie-consent", None),
    "links-pages": ("links-page", "gallery"),
    "timelines": ("timeline", "features"),
}

_FEATURE_TAGS = {
    "buttons": "actions",
    "cards": "cards",
    "icons": "icons",
    "logos": "logos",
    "list": "list",
    "star rating": "rating",
    "avatar image": "avatar",
    "pricing section": "plans",
    "pricing comparison section": "comparison",
    "mega menu": "mega-menu",
    "hamburger menu (desktop)": "desktop-menu-toggle",
    "newsletter sign up": "newsletter",
    "featured blog posts": "featured-content",
    "form": "form",
    "contact details": "contact-details",
    "accordion": "disclosure-list",
    "progress bar": "progress",
    "radio buttons": "radio-group",
    "checkboxes": "checkbox-group",
    "toggles": "toggles",
    "search bar": "search",
    "dropdown": "dropdown",
    "filters": "filters",
    "filter top": "filters",
    "filter left": "filters",
    "pagination": "pagination",
    "date": "date",
    "author": "author",
    "tags": "tags",
    "rich text": "rich-text",
    "table of contents": "table-of-contents",
    "table": "table",
    "overlapping images": "overlapping-images",
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _source_slug(value: str) -> str:
    """Normalize list slugs to get_component slugs without losing stored provenance."""
    value = str(value).strip()
    value = re.sub(r"^section_", "", value)
    value = re.sub(r"_component$", "", value)
    return value


def _tag_set(component: dict) -> set[str]:
    return {str(t).strip().lower() for t in (component.get("tags") or []) if str(t).strip()}


def _columns(tags: set[str]) -> set[int]:
    values = set()
    for tag in tags:
        match = re.fullmatch(r"(\d+)(?:\+)? columns?", tag)
        if match:
            values.add(int(match.group(1)))
    return values


def _alignment(tags: set[str]) -> set[str]:
    values = set()
    for side in ("left", "center", "right"):
        if f"text align {side}" in tags:
            values.add(side)
    return values


def _media_sides(tags: set[str]) -> set[str]:
    values = set()
    for side in ("left", "right", "top", "bottom", "center"):
        if f"image/video {side}" in tags:
            values.add(side)
    if "background image" in tags:
        values.add("background")
    return values


def _media_modes(tags: set[str]) -> set[str]:
    values = set()
    if "video lightbox" in tags:
        values.add("video-lightbox")
    if "multiple images" in tags:
        values.add("multiple-images")
    if "background image" in tags:
        values.add("background-image")
    if "background video" in tags:
        values.add("background-video")
    if "image lightbox" in tags:
        values.add("image-lightbox")
    if "overlapping images" in tags:
        values.add("overlapping-images")
    if "image" in tags or "avatar image" in tags:
        values.add("image")
    return values


def _interactions(tags: set[str]) -> set[str]:
    mapping = {
        "slider": "carousel",
        "tabs": "tabs",
        "video lightbox": "dialog",
        "image lightbox": "dialog",
        "accordion": "disclosure",
        "modal": "modal",
        "filters": "filter",
        "filter top": "filter",
        "filter left": "filter",
        "pagination": "pagination",
        "search bar": "search",
    }
    return {value for tag, value in mapping.items() if tag in tags}


def _ingredients(tags: set[str]) -> set[str]:
    return {value for tag, value in _FEATURE_TAGS.items() if tag in tags}


def _nav_skeleton(tags: set[str]) -> str:
    if "hamburger menu (desktop)" in tags:
        return "overlay-menu"
    if "mega menu" in tags:
        return "mega-menu"
    return "standard-nav"


def _footer_skeleton(tags: set[str]) -> str:
    if "newsletter sign up" in tags:
        return "newsletter-columns"
    if "contact details" in tags:
        return "contact-columns"
    if "text align center" in tags and not _columns(tags):
        return "compact-centered"
    if "cards" in tags:
        return "inset-columns"
    return "link-columns"


def _skeleton(tags: set[str], section_type: str = "") -> str:
    """Return structural identity; ingredient and mirror differences stay as axes."""
    if section_type == "navigation":
        return _nav_skeleton(tags)
    if section_type == "footer":
        return _footer_skeleton(tags)
    cols = _columns(tags)
    if "modal" in tags:
        return "modal"
    if "progress bar" in tags and "form" in tags:
        return "multi-step"
    if "accordion" in tags:
        return "disclosure-list"
    if "timeline section" in tags:
        return "timeline"
    if "table" in tags:
        return "table"
    if tags & {"filters", "filter top", "filter left"}:
        return "filterable-content"
    if "slider" in tags:
        return "carousel"
    if "tabs" in tags:
        return "tabs"
    if tags & {"background image", "background video"}:
        return "media-background"
    if 2 in cols and _media_sides(tags) & {"left", "right"}:
        return "content-media-split"
    if any(value > 1 for value in cols):
        return "repeated-grid"
    if "multiple images" in tags:
        return "media-collage"
    return "content-stack"


def _archetype(skeleton: str) -> str:
    return {
        "carousel": "cards",
        "tabs": "cards",
        "media-background": "overlay",
        "content-media-split": "split",
        "repeated-grid": "cards",
        "media-collage": "collage",
        "content-stack": "stack",
        "standard-nav": "stack",
        "mega-menu": "overlay",
        "overlay-menu": "overlay",
        "newsletter-columns": "split",
        "contact-columns": "split",
        "compact-centered": "stack",
        "inset-columns": "cards",
        "link-columns": "cards",
        "modal": "overlay",
        "multi-step": "stack",
        "disclosure-list": "stack",
        "timeline": "stack",
        "table": "cards",
        "filterable-content": "cards",
    }[skeleton]


def _position_axis(tags: set[str], prefix: str) -> set[str]:
    values = set()
    for tag in tags:
        if tag.startswith(prefix):
            values.add(_slug(tag.removeprefix(prefix).strip()))
    return values


def _slot_contract(section_type: str, ingredients: set[str], media_modes: set[str]) -> dict:
    if section_type == "navigation":
        return {
            "required": ["logo", "links", "mobileMenuToggle"],
            "optional": [
                "actions", "contactDetails", "dropdown", "featuredContent", "form",
                "megaMenu", "newsletter", "socialLinks",
            ],
        }
    if section_type == "footer":
        return {
            "required": ["logo", "linkColumns"],
            "optional": [
                "actions", "brandArt", "contactDetails", "legalLinks", "newsletter",
                "newsletterConsent", "socialLinks",
            ],
        }
    optional = sorted(ingredients | ({"media"} if media_modes else set()))
    return {
        "required": ["heading"] if section_type not in {
            "loader", "application-shell", "cookie-consent"
        } else [],
        "optional": optional,
    }


@dataclass
class RecipeAccumulator:
    recipe_id: str
    section_type: str
    builder_use_case: str | None
    category: str
    skeleton: str
    archetype: str
    exemplars: list[str] = field(default_factory=list)
    previews: list[str] = field(default_factory=list)
    columns: set[int] = field(default_factory=set)
    alignments: set[str] = field(default_factory=set)
    media_sides: set[str] = field(default_factory=set)
    media_modes: set[str] = field(default_factory=set)
    interactions: set[str] = field(default_factory=set)
    ingredients: set[str] = field(default_factory=set)
    source_tags: set[str] = field(default_factory=set)
    logo_positions: set[str] = field(default_factory=set)
    menu_positions: set[str] = field(default_factory=set)
    responsive_observations: list[dict] = field(default_factory=list)

    def add(self, component: dict, responsive: dict | None = None) -> None:
        tags = _tag_set(component)
        self.exemplars.append(str(component["slug"]))
        if component.get("preview"):
            self.previews.append(str(component["preview"]))
        self.columns.update(_columns(tags))
        self.alignments.update(_alignment(tags))
        self.media_sides.update(_media_sides(tags))
        self.media_modes.update(_media_modes(tags))
        self.interactions.update(_interactions(tags))
        self.ingredients.update(_ingredients(tags))
        self.source_tags.update(tags)
        self.logo_positions.update(_position_axis(tags, "logo "))
        self.menu_positions.update(_position_axis(tags, "menu "))
        if responsive:
            self.responsive_observations.append(responsive)

    def as_dict(self) -> dict:
        axes = {}
        for key, values in (
            ("columns", self.columns),
            ("textAlign", self.alignments),
            ("mediaSide", self.media_sides),
            ("mediaMode", self.media_modes),
            ("interaction", self.interactions),
            ("ingredients", self.ingredients),
            ("logoPosition", self.logo_positions),
            ("menuPosition", self.menu_positions),
        ):
            if values:
                axes[key] = sorted(values)
        responsive_rules = []
        inspected_slugs = []
        anatomy = {}
        for observation in self.responsive_observations:
            inspected_slugs.append(str(observation.get("componentSlug") or ""))
            responsive_rules.extend(observation.get("rules") or [])
            for key, values in (observation.get("anatomy") or {}).items():
                anatomy.setdefault(key, set()).update(values if isinstance(values, list) else [values])
        responsive_rules = [
            dict(rule) for rule in {
                json.dumps(rule, sort_keys=True): rule for rule in responsive_rules if isinstance(rule, dict)
            }.values()
        ]
        return {
            "id": self.recipe_id,
            "sectionType": self.section_type,
            "builderUseCase": self.builder_use_case,
            "sourceCategory": self.category,
            "structure": {
                "skeleton": self.skeleton,
                "archetype": self.archetype,
            },
            "slots": _slot_contract(self.section_type, self.ingredients, self.media_modes),
            "variantAxes": axes,
            "responsive": {
                "evidenceStatus": (
                    "source-inspected" if self.responsive_observations
                    else "pending-source-inspection"
                ),
                "breakpointModel": "mobile-first",
                "orientationIsVariant": bool(self.media_sides & {"left", "right"}),
                "rules": responsive_rules,
                "inspectedComponentSlugs": sorted(s for s in inspected_slugs if s),
            },
            "anatomyEvidence": {
                key: sorted(str(v) for v in values if str(v))
                for key, values in sorted(anatomy.items())
            },
            "physicsBindings": [
                "containment",
                "relationalRhythm",
                "surfaceContrast",
                *(("interaction",) if self.interactions or self.section_type == "navigation" else ()),
                *(("controlMeasure",) if self.section_type in {"navigation", "footer"} else ()),
            ],
            "provenance": {
                "source": "Relume Library MCP",
                "componentCount": len(self.exemplars),
                "componentSlugs": sorted(self.exemplars),
                "previewExamples": sorted(set(self.previews))[:3],
                "tags": sorted(self.source_tags),
                "normalization": "metadata-derived; inspect representative source before renderer promotion",
            },
        }


def load_inventory(inventory_dir: Path = INVENTORY_DIR) -> list[dict]:
    categories = []
    for path in sorted(inventory_dir.glob("*.json")):
        doc = json.loads(path.read_text())
        if doc.get("schemaVersion") != INVENTORY_SCHEMA_VERSION:
            raise ValueError(f"{path}: unsupported schemaVersion {doc.get('schemaVersion')!r}")
        categories.extend(doc.get("categories") or [])
    return categories


def load_responsive_evidence(path: Path = RESPONSIVE_EVIDENCE) -> dict[str, dict]:
    if not path.exists():
        return {}
    doc = yaml.safe_load(path.read_text()) or {}
    if doc.get("schemaVersion") != RESPONSIVE_SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schemaVersion {doc.get('schemaVersion')!r}")
    observations = doc.get("observations") or []
    return {
        _source_slug(str(observation["componentSlug"])): observation
        for observation in observations
        if isinstance(observation, dict) and observation.get("componentSlug")
    }


def compile_catalog(categories: Iterable[dict], responsive_evidence: dict[str, dict] | None = None) -> dict:
    accumulators: dict[str, RecipeAccumulator] = {}
    category_counts = {}
    component_slugs = set()
    duplicate_slugs = set()
    responsive_evidence = responsive_evidence or {}

    for category in categories:
        category_slug = str(category.get("slug") or "")
        if category_slug not in CATEGORY_TAXONOMY:
            raise ValueError(f"unmapped Relume category: {category_slug}")
        section_type, builder_use_case = CATEGORY_TAXONOMY[category_slug]
        components = category.get("components") or []
        category_counts[category_slug] = len(components)
        for component in components:
            component_slug = str(component.get("slug") or "")
            if not component_slug:
                raise ValueError(f"{category_slug}: component without slug")
            if component_slug in component_slugs:
                duplicate_slugs.add(component_slug)
            component_slugs.add(component_slug)
            tags = _tag_set(component)
            skeleton = _skeleton(tags, section_type)
            recipe_id = f"{section_type}-{skeleton}"
            acc = accumulators.get(recipe_id)
            if acc is None:
                acc = RecipeAccumulator(
                    recipe_id=recipe_id,
                    section_type=section_type,
                    builder_use_case=builder_use_case,
                    category=category_slug,
                    skeleton=skeleton,
                    archetype=_archetype(skeleton),
                )
                accumulators[recipe_id] = acc
            acc.add(component, responsive_evidence.get(_source_slug(component_slug)))

    recipes = [acc.as_dict() for _, acc in sorted(accumulators.items())]
    recipe_counts_by_category = {}
    for recipe in recipes:
        category = str(recipe.get("sourceCategory") or "")
        recipe_counts_by_category[category] = recipe_counts_by_category.get(category, 0) + 1
    responsive_recipe_count = sum(
        recipe["responsive"]["evidenceStatus"] == "source-inspected" for recipe in recipes
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "source": {
            "name": "Relume Library MCP",
            "kind": "structural-prior",
            "productRole": "content-structure-baseline",
            "storesVendoredSource": False,
            "ignoredVisualStyle": [
                "colors",
                "typography",
                "spacing",
                "class-names",
                "radii",
                "shadows",
                "aesthetic-defaults",
            ],
            "selectionPrecedence": [
                "active-brand-facts",
                "active-style-structure",
                "brand-neverDo-and-physics",
                "selected-structural-prior",
            ],
            "knownBiases": [
                "conventional-saas",
                "marketing-sites",
                "application-ui",
            ],
            "coverageLimit": (
                "Does not claim editorial, experimental, art-directed, or other "
                "high-variance structural coverage."
            ),
            "genreMergePolicy": (
                "Keep curated editorial and other high-variance corpora in separate "
                "provenance-bearing genre libraries with physics constraints; merge "
                "candidate sets at selection time, never into this baseline."
            ),
        },
        "coverage": {
            "categoryCount": len(category_counts),
            "componentCount": len(component_slugs),
            "recipeFamilyCount": len(recipes),
            "responsiveSourceInspectedRecipeCount": responsive_recipe_count,
            "responsiveSourcePendingRecipeCount": len(recipes) - responsive_recipe_count,
            "categories": dict(sorted(category_counts.items())),
            "recipeFamiliesByCategory": dict(sorted(recipe_counts_by_category.items())),
            "duplicateComponentSlugs": sorted(duplicate_slugs),
        },
        "recipes": recipes,
    }


def write_catalog(doc: dict, output: Path = GENERATED_CATALOG) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(doc, sort_keys=False, width=110))
    return output


def write_coverage_reports(
    doc: dict,
    json_output: Path = GENERATED_COVERAGE_JSON,
    markdown_output: Path = GENERATED_COVERAGE_MD,
) -> tuple[Path, Path]:
    coverage = doc.get("coverage") or {}
    json_output.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n")
    rows = [
        "# Relume Recipe Coverage",
        "",
        "Relume is a content-structure baseline, not visual style and not a template "
        "collection. Active brand/style data always wins.",
        "",
        f"- Categories: **{coverage.get('categoryCount', 0)}**",
        f"- Components: **{coverage.get('componentCount', 0)}**",
        f"- Recipe families: **{coverage.get('recipeFamilyCount', 0)}**",
        "- Responsive source-inspected families: "
        f"**{coverage.get('responsiveSourceInspectedRecipeCount', 0)}**",
        "- Responsive source-pending families: "
        f"**{coverage.get('responsiveSourcePendingRecipeCount', 0)}**",
        f"- Duplicate source slugs: **{len(coverage.get('duplicateComponentSlugs') or [])}**",
        "",
        "Scope note: coverage is biased toward conventional SaaS, marketing, and "
        "application UI. It does not claim editorial or experimental coverage; those "
        "corpora remain separate provenance-bearing genre libraries merged at selection time.",
        "",
        "## Category coverage",
        "",
        "| Relume category | Components | Recipe families |",
        "|---|---:|---:|",
    ]
    family_counts = coverage.get("recipeFamiliesByCategory") or {}
    for category, count in (coverage.get("categories") or {}).items():
        rows.append(f"| `{category}` | {count} | {family_counts.get(category, 0)} |")
    rows.extend([
        "",
        "Every component slug is retained in `catalog.generated.yaml` provenance. Responsive "
        "coverage means representative TSX was inspected for every normalized family; it "
        "does not claim every source component was fetched.",
        "",
    ])
    markdown_output.write_text("\n".join(rows))
    return json_output, markdown_output


def load_catalog(path: Path = STRUCTURAL_CATALOG) -> dict:
    if not path.exists():
        return {}
    doc = yaml.safe_load(path.read_text()) or {}
    expected = STRUCTURAL_SCHEMA_VERSION if path == STRUCTURAL_CATALOG else SCHEMA_VERSION
    if doc.get("schemaVersion") != expected:
        raise ValueError(f"{path}: unsupported schemaVersion {doc.get('schemaVersion')!r}")
    if expected == STRUCTURAL_SCHEMA_VERSION:
        assert_prompt_safe(doc)
    return doc


def match_recipes(
    catalog: dict,
    *,
    section_type: str | None = None,
    builder_use_case: str | None = None,
    skeleton: str | None = None,
    ingredients: Iterable[str] = (),
    responsive_required: bool = False,
) -> list[dict]:
    """Retrieve recipe families without materialising combinations.

    Exact section type/skeleton filters are hard. Ingredient requests score families
    by overlap, while source-inspected responsive evidence wins ties.
    """
    wanted = {str(value) for value in ingredients if str(value)}
    ranked = []
    for index, recipe in enumerate(catalog.get("recipes") or []):
        if section_type and recipe.get("sectionType") != section_type:
            continue
        if builder_use_case and recipe.get("builderUseCase") != builder_use_case:
            continue
        if skeleton and (recipe.get("structure") or {}).get("skeleton") != skeleton:
            continue
        responsive = recipe.get("responsive") or {}
        inspected = responsive.get("evidenceStatus") == "source-inspected"
        if responsive_required and not inspected:
            continue
        available = set((recipe.get("variantAxes") or {}).get("ingredients") or [])
        available.update((recipe.get("slots") or {}).get("optional") or [])
        overlap = len(wanted & available)
        ranked.append((-overlap, not inspected, index, recipe))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return [recipe for _, _, _, recipe in ranked]


def render_recipe_guidance(recipes: Iterable[dict], *, limit: int = 10) -> str:
    if limit > 3:
        raise ValueError("prompt-facing Relume selection is hard-capped at top-k=3")
    selected = list(recipes)[:limit]
    if not selected:
        return ""
    assert_prompt_safe(selected)
    lines = [
        "## SECTION RECIPE CANDIDATES (content-structure baseline; NEVER a visual template)",
        "",
        "FALLBACK ONLY. Choose structure and ingredient axes from these normalized families. Mirrored "
        "orientations and media substitutions are knobs, not separate templates. Preserve "
        "the listed responsive transitions; do not reduce them to desktop-only geometry.",
        "Relume contributes topology ONLY. Brand tokens, surfaces, spacing, components, "
        "media and copy bind after selection. No source visual or concrete value is available. "
        "Measured brand patterns > designed-from-brand patterns > compatible brand/style "
        "archetypes > this fallback. Stamp a chosen fallback with "
        "`structureProvenance: relume-fallback` and its `structureRecipeId`.",
        "This baseline is biased toward conventional SaaS, marketing, and application UI. "
        "Do not infer that it covers editorial or experimental structures. Those candidates "
        "belong to separate curated genre libraries and may be merged only at selection time.",
        "",
    ]
    for recipe in selected:
        structure = recipe.get("structure") or {}
        slots = recipe.get("slots") or {}
        axes = recipe.get("variantAxes") or {}
        responsive = recipe.get("responsive") or {}
        lines.append(
            f"- `{recipe.get('id')}` — section `{recipe.get('sectionType')}`, "
            f"archetype `{structure.get('archetype')}`, skeleton `{structure.get('skeleton')}`"
        )
        lines.append(
            "    - slots: required "
            f"{', '.join(slots.get('required') or []) or 'none'}; optional "
            f"{', '.join(slots.get('optional') or []) or 'none'}"
        )
        if axes:
            rendered_axes = "; ".join(
                f"{key}={','.join(map(str, values))}" for key, values in axes.items()
            )
            lines.append(f"    - variant axes: {rendered_axes}")
        rules = responsive.get("rules") or []
        if rules:
            rendered_rules = []
            for rule in rules[:8]:
                transition = f"{rule.get('axis')}: {rule.get('base')}"
                if rule.get("at"):
                    transition += f" → {rule.get('at')}:{rule.get('value')}"
                elif rule.get("value") and rule.get("value") != rule.get("base"):
                    transition += f" → {rule.get('value')}"
                rendered_rules.append(transition)
            lines.append(f"    - responsive: {'; '.join(rendered_rules)}")
        else:
            lines.append(
                "    - responsive: source inspection pending; do not infer unsupported transitions"
            )
    lines.append("")
    guidance = "\n".join(lines)
    assert_prompt_safe(guidance)
    return guidance


def guidance_for_use_cases(
    use_cases: Iterable[str],
    *,
    catalog: dict | None = None,
    per_use_case: int = 2,
) -> str:
    if per_use_case < 1 or per_use_case > 3:
        raise ValueError("per_use_case must be between 1 and 3")
    catalog = catalog if catalog is not None else load_catalog()
    selected = []
    seen = set()
    for use_case in use_cases:
        for recipe in match_recipes(catalog, builder_use_case=str(use_case))[:per_use_case]:
            if recipe.get("id") not in seen and len(selected) < 3:
                selected.append(recipe)
                seen.add(recipe.get("id"))
    return render_recipe_guidance(selected, limit=max(1, len(selected)))


def fallback_guidance(
    requested_use_cases: Iterable[str],
    *,
    higher_tier: dict[str, str] | None = None,
    ingredients_by_use_case: dict[str, Iterable[str]] | None = None,
    catalog: dict | None = None,
    top_k: int = 3,
) -> tuple[str, dict[str, list[str]]]:
    """Resolve only unsupported jobs and expose at most three structural candidates total."""
    if top_k < 1 or top_k > 3:
        raise ValueError("top_k must be between 1 and 3")
    higher_tier = higher_tier or {}
    ingredients_by_use_case = ingredients_by_use_case or {}
    catalog = catalog if catalog is not None else load_catalog()
    chosen: list[dict] = []
    selections: dict[str, list[str]] = {}
    seen: set[str] = set()
    for use_case in requested_use_cases:
        use_case = str(use_case)
        if not use_case or use_case == "footer" or use_case in higher_tier:
            continue
        matches = match_recipes(
            catalog,
            builder_use_case=use_case,
            ingredients=ingredients_by_use_case.get(use_case, ()),
        )
        for recipe in matches:
            recipe_id = str(recipe.get("id") or "")
            if not recipe_id or recipe_id in seen or len(chosen) >= top_k:
                continue
            chosen.append(recipe)
            seen.add(recipe_id)
            selections.setdefault(use_case, []).append(recipe_id)
        if len(chosen) >= top_k:
            break
    return render_recipe_guidance(chosen, limit=top_k) if chosen else "", selections


def main() -> None:
    categories = load_inventory()
    doc = compile_catalog(categories, load_responsive_evidence())
    output = write_catalog(doc)
    structural_output = write_structural_catalog(doc)
    write_coverage_reports(doc)
    print(f"wrote {output.relative_to(REPO_ROOT)}")
    print(f"wrote {structural_output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
