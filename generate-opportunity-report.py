#!/usr/bin/env python3

import argparse
import json
from collections import deque
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


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_history(path: Path, limit: int) -> list[dict]:
    if limit <= 0 or not path.exists():
        return []
    samples: deque[dict] = deque(maxlen=limit)
    with path.open(encoding="utf-8") as file:
        for line in file:
            raw = line.strip()
            if not raw:
                continue
            try:
                samples.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return list(samples)


def build_rows(score: dict, history: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for kit in KIT_NAMES:
        content_key = f"content_{kit}_requests_24h"
        organic_key = f"organic_non_bot_{kit}_referrals_24h"
        internal_key = f"internal_crossproperty_high_confidence_non_bot_referrals_to_{kit}_24h"
        crosspromo_key = f"crosspromo_non_bot_hits_to_{kit}_24h"

        content_requests = as_int(score.get(content_key, 0))
        organic_non_bot_referrals = as_int(score.get(organic_key, 0))
        internal_high_confidence_referrals = as_int(score.get(internal_key, 0))
        crosspromo_non_bot_hits = as_int(score.get(crosspromo_key, 0))

        if content_requests > 0:
            organic_rate = organic_non_bot_referrals / content_requests
            internal_rate = internal_high_confidence_referrals / content_requests
        else:
            organic_rate = 0.0
            internal_rate = 0.0

        growth_pct = 0.0
        if len(history) >= 2:
            first = as_int(history[0].get(content_key, 0))
            last = as_int(history[-1].get(content_key, 0))
            if first <= 0:
                growth_pct = 100.0 if last > 0 else 0.0
            else:
                growth_pct = ((last - first) / first) * 100.0

        rows.append(
            {
                "kit": kit,
                "content_requests_24h": content_requests,
                "organic_non_bot_referrals_24h": organic_non_bot_referrals,
                "internal_high_confidence_non_bot_referrals_24h": internal_high_confidence_referrals,
                "crosspromo_non_bot_hits_24h": crosspromo_non_bot_hits,
                "organic_non_bot_referral_rate": organic_rate,
                "internal_high_confidence_referral_rate": internal_rate,
                "content_growth_pct_window": round(growth_pct, 2),
            }
        )
    return rows


def score_rows(rows: list[dict]) -> list[dict]:
    max_content = max((row["content_requests_24h"] for row in rows), default=0)
    max_organic_rate = max((row["organic_non_bot_referral_rate"] for row in rows), default=0.0)
    max_internal_rate = max((row["internal_high_confidence_referral_rate"] for row in rows), default=0.0)

    for row in rows:
        demand_score = 0.0
        if max_content > 0:
            demand_score = row["content_requests_24h"] / max_content

        if max_organic_rate > 0:
            organic_gap_score = 1.0 - min(row["organic_non_bot_referral_rate"] / max_organic_rate, 1.0)
        else:
            organic_gap_score = 1.0

        if max_internal_rate > 0:
            internal_gap_score = 1.0 - min(row["internal_high_confidence_referral_rate"] / max_internal_rate, 1.0)
        else:
            internal_gap_score = 1.0

        momentum_score = clamp(max(row["content_growth_pct_window"], 0.0) / 200.0)
        activity_floor = clamp(row["content_requests_24h"] / 50.0)
        opportunity_raw = (
            0.5 * demand_score + 0.3 * organic_gap_score + 0.15 * internal_gap_score + 0.05 * momentum_score
        )
        opportunity_score = round(100.0 * opportunity_raw * activity_floor, 2)

        reasons: list[str] = []
        if row["content_requests_24h"] >= 50 and row["organic_non_bot_referrals_24h"] == 0:
            reasons.append("no organic non-bot referrals despite measurable traffic")
        if row["content_requests_24h"] >= 50 and row["internal_high_confidence_non_bot_referrals_24h"] == 0:
            reasons.append("no high-confidence internal referrals despite measurable traffic")
        if row["content_growth_pct_window"] >= 25 and row["organic_non_bot_referral_rate"] == 0:
            reasons.append("traffic is growing but discovery quality remains zero")
        if not reasons:
            reasons.append("organic and internal discovery rates are below stronger peer kits")

        if opportunity_score >= 70:
            priority_tier = "high"
        elif opportunity_score >= 40:
            priority_tier = "medium"
        else:
            priority_tier = "watch"

        recommended_primary_category = "S"
        if row["internal_high_confidence_non_bot_referrals_24h"] == 0 and row["content_requests_24h"] >= 50:
            recommended_primary_category = "I"
        if row["crosspromo_non_bot_hits_24h"] == 0 and row["content_requests_24h"] >= 50:
            recommended_primary_category = "M"

        row.update(
            {
                "opportunity_score": opportunity_score,
                "priority_tier": priority_tier,
                "recommended_primary_category": recommended_primary_category,
                "reasons": reasons,
                "organic_non_bot_referral_rate_pct": round(row["organic_non_bot_referral_rate"] * 100.0, 3),
                "internal_high_confidence_referral_rate_pct": round(
                    row["internal_high_confidence_referral_rate"] * 100.0,
                    3,
                ),
            }
        )

    return sorted(rows, key=lambda row: (-row["opportunity_score"], -row["content_requests_24h"], row["kit"]))


def build_report(score: dict, history: list[dict]) -> dict:
    scored_rows = score_rows(build_rows(score, history))
    top_opportunities = scored_rows[:3]
    generated_at = score.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "generated_at": generated_at,
        "history_samples_analyzed": len(history),
        "kits_analyzed": len(KIT_NAMES),
        "scoring": {
            "formula": "score = activity_floor * (0.5*demand + 0.3*organic_gap + 0.15*internal_gap + 0.05*momentum)",
            "activity_floor_full_at_content_requests": 50,
            "momentum_full_at_growth_pct": 200,
            "higher_score_means": "higher current demand with weaker organic/internal discovery coverage",
        },
        "top_opportunities": top_opportunities,
        "kit_rankings": scored_rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate kit opportunity rankings from score/history metrics.")
    parser.add_argument("--score", required=True, help="Path to metrics/score.json")
    parser.add_argument("--history", required=True, help="Path to metrics/history.jsonl")
    parser.add_argument("--output", required=True, help="Path to write opportunity report JSON")
    parser.add_argument("--history-limit", type=int, default=10, help="How many recent history rows to analyze")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    score_path = Path(args.score)
    history_path = Path(args.history)
    output_path = Path(args.output)
    score = load_json(score_path)
    history = load_history(history_path, args.history_limit)
    report = build_report(score, history)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
