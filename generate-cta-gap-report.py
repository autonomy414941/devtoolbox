#!/usr/bin/env python3

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

KIT_NAMES = (
    "datekit",
    "budgetkit",
    "healthkit",
    "sleepkit",
    "focuskit",
    "opskit",
    "studykit",
    "careerkit",
    "housingkit",
    "taxkit",
)


def as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def as_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def source_slug(path: str) -> str:
    cleaned = path.split("?", 1)[0].split("#", 1)[0].strip().strip("/")
    if not cleaned:
        return "home"
    slug = cleaned.split("/")[-1].strip().lower()
    if slug.endswith(".html"):
        slug = slug[:-5]
    return slug


def is_candidate_source_path(path: str) -> bool:
    if path == "/":
        return True
    if path.startswith("/blog/") and len(path.strip("/").split("/")) >= 2:
        return True
    if path.startswith("/tools/") and len(path.strip("/").split("/")) >= 2:
        return True
    if path.startswith("/cheatsheets/") and len(path.strip("/").split("/")) >= 2:
        return True
    return False


def build_target_kits(opportunity: dict, score: dict) -> list[dict]:
    targets: list[dict] = []
    seen: set[str] = set()
    for row in opportunity.get("top_opportunities", []):
        if not isinstance(row, dict):
            continue
        kit = str(row.get("kit", "")).lower()
        if kit not in KIT_NAMES or kit in seen:
            continue
        targets.append(
            {
                "kit": kit,
                "target_opportunity_score": as_float(row.get("opportunity_score", 0)),
                "recommended_primary_category": str(row.get("recommended_primary_category", "M")),
                "quality_adjusted_human_signal_rate_pct": as_float(
                    row.get("quality_adjusted_human_signal_rate_pct", 0)
                ),
                "human_signal_hits_24h": as_int(row.get("human_signal_hits_24h", 0)),
                "content_requests_24h": as_int(score.get(f"content_{kit}_requests_24h", 0)),
            }
        )
        seen.add(kit)
        if len(targets) >= 3:
            break

    top_kit = str(score.get("top_opportunity_kit_24h", "")).lower()
    if top_kit in KIT_NAMES and top_kit not in seen:
        targets.insert(
            0,
            {
                "kit": top_kit,
                "target_opportunity_score": as_float(score.get("top_opportunity_score_24h", 0)),
                "recommended_primary_category": str(
                    score.get("top_opportunity_recommended_primary_category_24h", "M")
                ),
                "quality_adjusted_human_signal_rate_pct": as_float(
                    score.get("top_opportunity_quality_adjusted_human_signal_rate_pct_24h", 0)
                ),
                "human_signal_hits_24h": as_int(score.get("top_opportunity_human_signal_hits_24h", 0)),
                "content_requests_24h": as_int(score.get(f"content_{top_kit}_requests_24h", 0)),
            },
        )
        seen.add(top_kit)

    if targets:
        return targets[:3]

    ranked = sorted(
        KIT_NAMES,
        key=lambda kit: as_int(score.get(f"content_{kit}_requests_24h", 0)),
        reverse=True,
    )
    for kit in ranked[:3]:
        targets.append(
            {
                "kit": kit,
                "target_opportunity_score": 0.0,
                "recommended_primary_category": "M",
                "quality_adjusted_human_signal_rate_pct": 0.0,
                "human_signal_hits_24h": as_int(
                    score.get(f"organic_non_bot_{kit}_referrals_24h", 0)
                    + score.get(f"internal_crossproperty_high_confidence_non_bot_referrals_to_{kit}_24h", 0)
                    + score.get(f"crosspromo_non_bot_hits_to_{kit}_24h", 0)
                ),
                "content_requests_24h": as_int(score.get(f"content_{kit}_requests_24h", 0)),
            }
        )
    return targets


def parse_non_bot_campaign_pairs(traffic: dict) -> dict[str, dict[str, int]]:
    by_kit: dict[str, dict[str, int]] = {kit: {} for kit in KIT_NAMES}
    for item in traffic.get("crosspromo_non_bot_campaign_source_target_sections", []):
        if not isinstance(item, dict):
            continue
        pair = str(item.get("pair", "")).strip()
        count = as_int(item.get("count", 0))
        if count <= 0 or "->" not in pair:
            continue
        source, target = pair.split("->", 1)
        source_slug_value = source.strip().lower()
        target_section = target.strip().lower()
        if not source_slug_value or target_section not in by_kit:
            continue
        existing = by_kit[target_section].get(source_slug_value, 0)
        by_kit[target_section][source_slug_value] = existing + count
    return by_kit


def extract_candidate_sources(traffic: dict, max_source_pages: int) -> list[dict]:
    paths_by_hits: dict[str, int] = {}
    for key in ("top_pages", "top_organic_non_bot_pages", "top_organic_pages"):
        for item in traffic.get(key, []):
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", "")).strip()
            hits = as_int(item.get("count", 0))
            if hits <= 0 or not is_candidate_source_path(path):
                continue
            previous = paths_by_hits.get(path, 0)
            if hits > previous:
                paths_by_hits[path] = hits

    ranked = sorted(paths_by_hits.items(), key=lambda row: (-row[1], row[0]))[:max_source_pages]
    return [
        {
            "source_path": path,
            "source_slug": source_slug(path),
            "source_hits_24h": hits,
        }
        for path, hits in ranked
    ]


def source_rationale(path: str) -> str:
    if path == "/":
        return "homepage has the broadest on-site entry flow but no measured non-bot campaign path to this kit"
    if path.startswith("/blog/"):
        return "high blog traffic page lacks measured non-bot campaign flow to this kit"
    if path.startswith("/tools/"):
        return "high tool traffic page lacks measured non-bot campaign flow to this kit"
    if path.startswith("/cheatsheets/"):
        return "high cheatsheet traffic page lacks measured non-bot campaign flow to this kit"
    return "high-traffic source lacks measured non-bot campaign flow to this kit"


def build_report(
    score: dict,
    traffic: dict,
    opportunity: dict,
    max_source_pages: int,
    per_kit_limit: int,
    top_actions_limit: int,
) -> dict:
    generated_at = (
        str(score.get("timestamp", "")).strip()
        or str((traffic.get("summary") or {}).get("generated_at", "")).strip()
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    candidate_sources = extract_candidate_sources(traffic, max_source_pages=max_source_pages)
    observed_by_kit = parse_non_bot_campaign_pairs(traffic)
    target_kits = build_target_kits(opportunity, score)

    kit_reports: list[dict] = []
    top_actions: list[dict] = []

    for target in target_kits:
        kit = target["kit"]
        opportunity_score = as_float(target["target_opportunity_score"])
        observed_sources = observed_by_kit.get(kit, {})
        gap_rows: list[dict] = []
        for source in candidate_sources:
            slug = source["source_slug"]
            if slug in observed_sources:
                continue
            gap_priority = round(source["source_hits_24h"] * (1.0 + (opportunity_score / 100.0)), 2)
            gap_rows.append(
                {
                    "source_path": source["source_path"],
                    "source_slug": slug,
                    "source_hits_24h": source["source_hits_24h"],
                    "gap_priority_score": gap_priority,
                    "rationale": source_rationale(source["source_path"]),
                }
            )

        gap_rows.sort(key=lambda row: (-row["gap_priority_score"], -row["source_hits_24h"], row["source_path"]))
        top_source_gaps = gap_rows[:per_kit_limit]

        kit_report = {
            **target,
            "existing_non_bot_campaign_source_count_24h": len(observed_sources),
            "existing_non_bot_campaign_hits_24h": sum(observed_sources.values()),
            "candidate_source_pages_evaluated": len(candidate_sources),
            "source_gap_count": len(gap_rows),
            "top_source_gaps": top_source_gaps,
        }
        kit_reports.append(kit_report)

        for row in top_source_gaps:
            top_actions.append(
                {
                    "kit": kit,
                    "recommended_primary_category": target["recommended_primary_category"],
                    "target_opportunity_score": round(opportunity_score, 2),
                    "source_path": row["source_path"],
                    "source_slug": row["source_slug"],
                    "source_hits_24h": row["source_hits_24h"],
                    "gap_priority_score": row["gap_priority_score"],
                    "rationale": row["rationale"],
                }
            )

    top_actions.sort(key=lambda row: (-row["gap_priority_score"], -row["source_hits_24h"], row["source_path"]))
    top_actions = top_actions[:top_actions_limit]

    return {
        "generated_at": generated_at,
        "window_hours": as_int((traffic.get("summary") or {}).get("window_hours", 24)),
        "candidate_source_pages_analyzed": len(candidate_sources),
        "kits_analyzed": len(kit_reports),
        "strategy": {
            "candidate_source_pool": "homepage + top blog/tool/cheatsheet pages by clean hits",
            "gap_definition": "source page has no measured non-bot campaign source->target pair for the target kit in the last 24h",
            "priority_formula": "gap_priority_score = source_hits_24h * (1 + target_opportunity_score/100)",
        },
        "target_kits": kit_reports,
        "top_actions": top_actions,
        "coverage_summary": {
            "unique_candidate_source_slugs_analyzed": len(
                {source["source_slug"] for source in candidate_sources}
            ),
            "unique_observed_non_bot_source_slugs": len(
                {
                    slug
                    for kit_map in observed_by_kit.values()
                    for slug, count in kit_map.items()
                    if count > 0
                }
            ),
            "top_gap_target_kit": top_actions[0]["kit"] if top_actions else "",
            "top_gap_source_page": top_actions[0]["source_path"] if top_actions else "",
            "top_gap_priority_score": top_actions[0]["gap_priority_score"] if top_actions else 0,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate source-page CTA gap recommendations for high-opportunity kits."
    )
    parser.add_argument("--score", required=True, help="Path to metrics/score.json")
    parser.add_argument("--traffic", required=True, help="Path to metrics/traffic_report.json")
    parser.add_argument("--opportunity", required=True, help="Path to metrics/opportunity_report.json")
    parser.add_argument("--output", required=True, help="Path to write CTA gap report JSON")
    parser.add_argument("--max-source-pages", type=int, default=80, help="Max source pages to evaluate")
    parser.add_argument("--per-kit-limit", type=int, default=5, help="Max source gaps to keep per kit")
    parser.add_argument("--top-actions-limit", type=int, default=12, help="Max combined actions in output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    score = load_json(Path(args.score))
    traffic = load_json(Path(args.traffic))
    opportunity = load_json(Path(args.opportunity))
    report = build_report(
        score=score,
        traffic=traffic,
        opportunity=opportunity,
        max_source_pages=max(1, args.max_source_pages),
        per_kit_limit=max(1, args.per_kit_limit),
        top_actions_limit=max(1, args.top_actions_limit),
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
