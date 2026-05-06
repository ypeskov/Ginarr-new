#!/usr/bin/env python3
"""Compute weight + calorie statistics from a kcal.peskov.info dump.

Input: a JSON file produced by fitness-fetch, with shape
  {"weight": [{"weight": kg, "recorded_at": iso}, ...],
   "food":   [{"food": name, "calories": int, "weight": grams,
               "kcal_per_100g": int, "fats"?: g, "proteins"?: g,
               "meal_datetime": iso}, ...]}

Output: a single JSON object on stdout with computed stats. The digest skill
formats this for the user; recommendations are an LLM job, not this script's.

Usage:
  python3 analyze.py <path-to-json> [--window 7|30|90|365]
  python3 analyze.py --auto [--days N]   # picks newest *_both.json from the
                                          # standard data dir; --days hints
                                          # the preferred range
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, date
from glob import glob

DATA_SUBPATH = "wiki/entities/fitness/_data"


def parse_iso_date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()


def closest_to(target, weights):
    return min(weights, key=lambda x: abs((x[0] - target).days))


def pick_latest(days_hint):
    root = os.environ.get("GINARR_VAULT_ROOT")
    if not root:
        print("error: GINARR_VAULT_ROOT not set", file=sys.stderr)
        sys.exit(2)
    pattern = os.path.join(root, DATA_SUBPATH, "*_both.json")
    candidates = glob(pattern)
    if not candidates:
        print(f"error: no _both.json files in {os.path.dirname(pattern)}", file=sys.stderr)
        sys.exit(1)
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


def weight_stats(weights, latest_date, latest_w):
    out = {
        "latest_kg": latest_w,
        "latest_date": latest_date.isoformat(),
        "entries": len(weights),
    }
    for d in (7, 30, 90, 180, 365):
        target = latest_date - timedelta(days=d)
        if weights[0][0] > target:
            continue
        ref_date, ref_w = closest_to(target, weights)
        out[f"vs_{d}d"] = {
            "ref_date": ref_date.isoformat(),
            "ref_kg": ref_w,
            "delta_kg": round(latest_w - ref_w, 2),
        }
    min_d, min_w = min(weights, key=lambda x: x[1])
    max_d, max_w = max(weights, key=lambda x: x[1])
    out["min"] = {"date": min_d.isoformat(), "kg": min_w}
    out["max"] = {"date": max_d.isoformat(), "kg": max_w}
    if "vs_30d" in out:
        days = (latest_date - date.fromisoformat(out["vs_30d"]["ref_date"])).days
        if days > 0:
            out["recent_kg_per_week"] = round(out["vs_30d"]["delta_kg"] / days * 7, 2)
    return out


def food_window(food_by_day, latest_date, days):
    cutoff = latest_date - timedelta(days=days)
    window = {k: v for k, v in food_by_day.items() if k >= cutoff and k <= latest_date}
    if not window:
        return None
    macro_days = {k: v for k, v in window.items() if v["has_macro"]}

    kcal_vals = [v["kcal"] for v in window.values()]
    mean_kcal = sum(kcal_vals) / len(kcal_vals)
    mean_p_all = sum(v["protein"] for v in window.values()) / len(window)
    mean_f_all = sum(v["fat"] for v in window.values()) / len(window)
    max_d = max(window.items(), key=lambda x: x[1]["kcal"])
    min_d = min(window.items(), key=lambda x: x[1]["kcal"])

    out = {
        "days_logged": len(window),
        "days_in_window": days,
        "mean_kcal": round(mean_kcal),
        "mean_protein_g_all_days": round(mean_p_all, 1),
        "mean_fat_g_all_days": round(mean_f_all, 1),
        "max_day": {"date": max_d[0].isoformat(), "kcal": round(max_d[1]["kcal"])},
        "min_day": {"date": min_d[0].isoformat(), "kcal": round(min_d[1]["kcal"])},
        "macro_days": len(macro_days),
    }
    if macro_days:
        out["mean_protein_g"] = round(sum(v["protein"] for v in macro_days.values()) / len(macro_days), 1)
        out["mean_fat_g"] = round(sum(v["fat"] for v in macro_days.values()) / len(macro_days), 1)
    return out


def food_stats(food, latest_date, windows):
    by_day = defaultdict(lambda: {"kcal": 0, "protein": 0, "fat": 0, "count": 0, "has_macro": False})
    for f in food:
        d = parse_iso_date(f["meal_datetime"])
        by_day[d]["kcal"] += f.get("calories", 0) or 0
        by_day[d]["protein"] += f.get("proteins", 0) or 0
        by_day[d]["fat"] += f.get("fats", 0) or 0
        by_day[d]["count"] += 1
        if f.get("proteins") is not None or f.get("fats") is not None:
            by_day[d]["has_macro"] = True

    out = {
        "total_entries": len(food),
        "days_logged_total": len(by_day),
    }
    if by_day:
        out["earliest_log"] = min(by_day).isoformat()
        out["latest_log"] = max(by_day).isoformat()
        macro_days_all = sorted(d for d, v in by_day.items() if v["has_macro"])
        if macro_days_all:
            out["macro_tracking_started"] = macro_days_all[0].isoformat()
    out["windows"] = {}
    for w in windows:
        stats = food_window(by_day, latest_date, w)
        if stats:
            out["windows"][f"{w}d"] = stats
    return out


def lbm_estimate(weight_kg):
    """Lean body mass range under standard body-fat assumptions for someone in
    long recovery from severe obesity (current BMI still in the obese range).

    The skill prompt is the source of truth for *which* assumption to apply;
    this function just exposes the math so the digest doesn't have to recompute
    in the LLM. Both `low` and `high` are returned and the digest picks the
    band it wants to talk about.
    """
    return {
        "weight_kg": weight_kg,
        "assumed_body_fat_pct": {"low": 30, "mid": 35, "high": 40},
        "lbm_kg": {
            "at_30pct": round(weight_kg * 0.70, 1),
            "at_35pct": round(weight_kg * 0.65, 1),
            "at_40pct": round(weight_kg * 0.60, 1),
        },
        "note": "Use LBM (or target weight at BMI 25) as the denominator for protein-per-kg targets, not total body weight.",
    }


def main():
    p = argparse.ArgumentParser(description="Compute fitness stats from a kcal dump")
    p.add_argument("path", nargs="?", help="Path to JSON dump")
    p.add_argument("--auto", action="store_true", help="Pick newest _both.json from vault")
    p.add_argument("--days", type=int, default=30,
                   help="Preferred analysis window in days (default 30)")
    args = p.parse_args()

    if args.auto and args.path:
        print("error: pass either a path or --auto, not both", file=sys.stderr)
        sys.exit(2)
    if not args.auto and not args.path:
        print("error: provide a path or --auto", file=sys.stderr)
        sys.exit(2)

    path = args.path if args.path else pick_latest(args.days)

    with open(path) as f:
        data = json.load(f)

    weights = sorted(
        [(parse_iso_date(w["recorded_at"]), w["weight"]) for w in data.get("weight", [])]
    )

    result = {
        "source_file": path,
        "weight_available": bool(weights),
        "food_available": bool(data.get("food")),
    }

    if weights:
        latest_date, latest_w = weights[-1]
        result["weight"] = weight_stats(weights, latest_date, latest_w)
        result["lbm"] = lbm_estimate(latest_w)
        latest_for_food = latest_date
    else:
        latest_for_food = date.today()

    if data.get("food"):
        result["food"] = food_stats(data["food"], latest_for_food, [7, 30, 90, 365])

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
