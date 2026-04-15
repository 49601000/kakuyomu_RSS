#!/usr/bin/env python3
"""Generate RSS feed XML for a Kakuyomu work page."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KakuyomuRSS/1.0"
WORK_URL_BASE = "https://kakuyomu.jp/works/"


class KakuyomuRSSError(Exception):
    """Raised when feed generation fails."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an RSS feed XML from a Kakuyomu work URL/ID."
    )
    parser.add_argument("work", help="Kakuyomu work URL or work ID")
    parser.add_argument(
        "-o",
        "--output",
        help="Output XML file path (default: stdout)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of latest episodes in feed (0 = all)",
    )
    return parser.parse_args()


def extract_work_id(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"\d{10,}", value):
        return value

    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise KakuyomuRSSError("作品IDまたは https://kakuyomu.jp/works/... のURLを指定してください。")

    m = re.search(r"/works/(\d{10,})", parsed.path)
    if not m:
        raise KakuyomuRSSError("URLから作品IDを抽出できませんでした。")
    return m.group(1)


def fetch_html(work_id: str) -> str:
    url = f"{WORK_URL_BASE}{work_id}"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()
    return response.text


def extract_next_data(html: str) -> dict:
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        html,
        flags=re.DOTALL,
    )
    if not m:
        raise KakuyomuRSSError("__NEXT_DATA__ が見つかりません。ページ構造が変更された可能性があります。")

    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        raise KakuyomuRSSError("__NEXT_DATA__ のJSON解析に失敗しました。") from exc


def resolve_work(state: dict, work_id: str) -> dict:
    root = state.get("ROOT_QUERY", {})
    key = f'work({{"id":"{work_id}"}})'
    work_ref = root.get(key)

    if not work_ref:
        for k, v in root.items():
            if k.startswith("work(") and work_id in k:
                work_ref = v
                break
    if not work_ref or "__ref" not in work_ref:
        raise KakuyomuRSSError("作品データを取得できませんでした。作品が存在しない可能性があります。")

    work_obj = state.get(work_ref["__ref"])
    if not work_obj:
        raise KakuyomuRSSError("作品データ参照の解決に失敗しました。")
    return work_obj


def collect_episodes(state: dict, work_obj: dict) -> list[dict]:
    episodes: list[dict] = []
    seen_ids: set[str] = set()

    for chapter_ref in work_obj.get("tableOfContentsV2", []):
        chapter = state.get(chapter_ref.get("__ref", ""))
        if not chapter:
            continue

        for ep_ref in chapter.get("episodeUnions", []):
            episode = state.get(ep_ref.get("__ref", ""))
            if not episode:
                continue

            episode_id = episode.get("id")
            title = episode.get("title")
            published_at = episode.get("publishedAt")
            if not episode_id or not title or not published_at:
                continue
            if episode_id in seen_ids:
                continue
            seen_ids.add(episode_id)

            episodes.append(
                {
                    "id": str(episode_id),
                    "title": str(title),
                    "publishedAt": str(published_at),
                }
            )

    episodes.sort(key=lambda x: x["publishedAt"], reverse=True)
    return episodes


def resolve_author_name(state: dict, work_obj: dict) -> str:
    author = work_obj.get("author")
    if isinstance(author, dict):
        if "activityName" in author and author["activityName"]:
            return str(author["activityName"])
        ref = author.get("__ref")
        if ref and ref in state:
            ref_obj = state[ref]
            for key in ("activityName", "name", "screenName"):
                if ref_obj.get(key):
                    return str(ref_obj[key])
    if isinstance(author, str) and author:
        return author
    return "Unknown author"


def to_rfc2822(iso_str: str) -> str:
    dt_obj = dt.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt_obj.strftime("%a, %d %b %Y %H:%M:%S %z")


def build_rss_xml(state: dict, work_id: str, work_obj: dict, episodes: list[dict], limit: int) -> str:
    if limit > 0:
        episodes = episodes[:limit]

    work_url = f"{WORK_URL_BASE}{work_id}"
    title = work_obj.get("title", f"Work {work_id}")
    author = resolve_author_name(state=state, work_obj=work_obj)
    description = work_obj.get("introduction") or work_obj.get("catchphrase") or "Kakuyomu work updates"

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = f"{title} / {author}"
    ET.SubElement(channel, "link").text = work_url
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "language").text = "ja"
    ET.SubElement(channel, "lastBuildDate").text = dt.datetime.now(dt.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S %z"
    )

    for episode in episodes:
        ep_url = f"{work_url}/episodes/{episode['id']}"
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = episode["title"]
        ET.SubElement(item, "link").text = ep_url
        ET.SubElement(item, "guid", isPermaLink="true").text = ep_url
        ET.SubElement(item, "pubDate").text = to_rfc2822(episode["publishedAt"])
        ET.SubElement(item, "description").text = f"{title} の更新話: {episode['title']}"

    xml_bytes = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


def main() -> int:
    args = parse_args()
    try:
        work_id = extract_work_id(args.work)
        html = fetch_html(work_id)
        next_data = extract_next_data(html)
        state = next_data["props"]["pageProps"]["__APOLLO_STATE__"]
        work_obj = resolve_work(state, work_id)
        episodes = collect_episodes(state, work_obj)
        if not episodes:
            raise KakuyomuRSSError("公開話データが見つかりませんでした。")
        xml = build_rss_xml(state, work_id, work_obj, episodes, args.limit)
    except requests.RequestException as exc:
        print(f"HTTP取得に失敗: {exc}", file=sys.stderr)
        return 1
    except (KakuyomuRSSError, KeyError) as exc:
        print(f"RSS生成に失敗: {exc}", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(xml)
            f.write("\n")
    else:
        print(xml)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
