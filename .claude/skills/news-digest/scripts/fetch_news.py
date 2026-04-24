#!/usr/bin/env python3
"""Fetch news from RSS feeds and Hacker News API, output as JSON.

Usage:
  python3 scripts/fetch_news.py [--categories ai it ua] [--max-items N] [--since HOURS]

Categories: ai, it, ua. Default: all.
--since: Only include articles published within the last N hours (default: 14).

Output: JSON object with category keys, each containing an array of articles.
  Each article: {title, link, date, summary, source} or {error}.
Exit codes: 0 = success, 1 = all sources failed.
"""

import feedparser
import urllib.request
import json
import sys
import argparse
import re
import time
import calendar
from datetime import datetime, timezone, timedelta


FEEDS = {
    "ai": [
        ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
        ("DeepMind Blog", "https://deepmind.google/blog/rss.xml"),
        ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
        ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
    ],
    "it": [
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ],
    "ua": [
        ("Ukrainska Pravda", "https://www.pravda.com.ua/rss/"),
        ("NV.ua", "https://nv.ua/rss/all.xml"),
        ("Liga.net", "https://www.liga.net/all/rss.xml"),
    ],
}


def parse_feed(source_name, url, max_items=20, cutoff=None):
    try:
        d = feedparser.parse(url)
        items = []
        for e in d.entries[:max_items]:
            pub_time = None
            if hasattr(e, "published_parsed") and e.published_parsed:
                pub_time = e.published_parsed
            elif hasattr(e, "updated_parsed") and e.updated_parsed:
                pub_time = e.updated_parsed

            # Filter by date if cutoff is set
            if cutoff and pub_time:
                entry_dt = datetime.fromtimestamp(calendar.timegm(pub_time), tz=timezone.utc)
                if entry_dt < cutoff:
                    continue
            # Skip entries with no date when filtering is active
            if cutoff and not pub_time:
                continue

            published = time.strftime("%Y-%m-%d %H:%M", pub_time) if pub_time else ""
            desc = ""
            if hasattr(e, "summary"):
                desc = re.sub(r"<[^<]+?>", "", e.summary)[:300]
            items.append({
                "title": e.get("title", ""),
                "link": e.get("link", ""),
                "date": published,
                "summary": desc,
                "source": source_name,
            })
        return items
    except Exception as ex:
        return [{"error": str(ex), "source": source_name}]


def fetch_hn_top(n=30, cutoff=None):
    try:
        req = urllib.request.Request(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers={"User-Agent": "curl/8.0"},
        )
        ids = json.loads(urllib.request.urlopen(req, timeout=10).read())[:n]
        items = []
        for sid in ids:
            req2 = urllib.request.Request(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                headers={"User-Agent": "curl/8.0"},
            )
            story = json.loads(urllib.request.urlopen(req2, timeout=5).read())
            if story and story.get("type") == "story":
                entry_dt = datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc)
                if cutoff and entry_dt < cutoff:
                    continue
                items.append({
                    "title": story.get("title", ""),
                    "link": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    "date": entry_dt.strftime("%Y-%m-%d %H:%M"),
                    "score": story.get("score", 0),
                    "summary": "",
                    "source": "Hacker News",
                })
        return items
    except Exception as ex:
        return [{"error": str(ex), "source": "Hacker News"}]


def main():
    parser = argparse.ArgumentParser(description="Fetch news from RSS and HN")
    parser.add_argument("--categories", nargs="+", choices=["ai", "it", "ua"],
                        default=["ai", "it", "ua"], help="Categories to fetch")
    parser.add_argument("--max-items", type=int, default=15,
                        help="Max items per feed (default: 15)")
    parser.add_argument("--since", type=int, default=14,
                        help="Only include articles from the last N hours (default: 14)")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.since)
    results = {}

    for cat in args.categories:
        items = []
        if cat == "it":
            items.extend(fetch_hn_top(20, cutoff=cutoff))
        for source_name, url in FEEDS.get(cat, []):
            items.extend(parse_feed(source_name, url, args.max_items, cutoff=cutoff))
        results[cat] = items

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
