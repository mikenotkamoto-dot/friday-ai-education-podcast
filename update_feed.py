#!/usr/bin/env python3
"""Build the static FRIDAY AI Education podcast feed from the local walkcast library."""
from __future__ import annotations

from datetime import datetime
from email.utils import formatdate
from pathlib import Path
import hashlib
import html
import json
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

SRC = Path('/Users/emilealbert/baeten-labs/friday/walkcasts/daily-ai-education')
PUBLIC = Path(__file__).resolve().parent / 'docs'
SECRET_PATH = 'feed-9c7b3d1a4f2e'
BASE_URL = 'https://mikenotkamoto-dot.github.io/friday-ai-education-podcast'


def ffprobe_duration(path: Path) -> str:
    try:
        res = subprocess.run(
            [
                '/opt/homebrew/bin/ffprobe', '-v', 'error',
                '-show_entries', 'format=duration', '-of', 'default=nk=1:nw=1',
                str(path),
            ],
            text=True,
            capture_output=True,
            timeout=20,
        )
        if res.returncode == 0 and res.stdout.strip():
            secs = int(float(res.stdout.strip()))
            return f'{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}'
    except Exception:
        return ''
    return ''


def build() -> dict:
    (PUBLIC / 'episodes').mkdir(parents=True, exist_ok=True)
    feed_dir = PUBLIC / SECRET_PATH
    feed_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict] = []
    source_dirs = {p.name: p for p in (SRC / 'episodes').glob('*-ep-*') if p.is_dir()}
    public_dirs = {p.name: p for p in (PUBLIC / 'episodes').glob('*-ep-*') if p.is_dir()}
    # Union preserves already-published episodes whose original local source was
    # archived, while allowing newly generated episodes to be added.
    for name in sorted(set(source_dirs) | set(public_dirs)):
        source_dir = source_dirs.get(name)
        public_dir = public_dirs.get(name)
        day_dir = source_dir or public_dir
        if day_dir is None:
            continue
        candidates = list(source_dir.glob('*.mp3')) if source_dir else []
        if not candidates and public_dir:
            candidates = list(public_dir.glob('*.mp3'))
        if not candidates:
            continue
        match = re.match(r'(\d{4}-\d{2}-\d{2})-ep-(\d{3})-(.+)', name)
        if not match:
            continue
        date, ep, slug = match.groups()
        src_mp3 = candidates[0]
        dest_dir = PUBLIC / 'episodes' / name
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_mp3 = dest_dir / src_mp3.name
        if src_mp3.resolve() != dest_mp3.resolve() and (not dest_mp3.exists() or dest_mp3.stat().st_size != src_mp3.stat().st_size):
            shutil.copy2(src_mp3, dest_mp3)

        pdf_rel = None
        pdf_candidates = list((SRC / 'printable-packs').glob(f'{date}-ep-{ep}-*-claude.pdf'))
        if not pdf_candidates:
            pdf_candidates = list(dest_dir.glob('*-claude.pdf'))
        if pdf_candidates:
            src_pdf = pdf_candidates[0]
            dest_pdf = dest_dir / src_pdf.name
            if src_pdf.resolve() != dest_pdf.resolve() and (not dest_pdf.exists() or dest_pdf.stat().st_size != src_pdf.stat().st_size):
                shutil.copy2(src_pdf, dest_pdf)
            pdf_rel = f'episodes/{name}/{src_pdf.name}'

        items.append({
            'date': date,
            'ep': ep,
            'title': ' '.join(word.capitalize() for word in slug.split('-')),
            'mp3_rel': f'episodes/{name}/{dest_mp3.name}',
            'pdf_rel': pdf_rel,
            'size': dest_mp3.stat().st_size,
            'mtime': dest_mp3.stat().st_mtime,
            'duration': ffprobe_duration(dest_mp3),
        })

    if not items:
        raise RuntimeError(f'Refusing to publish an empty feed; no MP3 episodes found under {SRC / "episodes"} or {PUBLIC / "episodes"}')

    feed_path = feed_dir / 'feed.xml'
    previous_count = 0
    if feed_path.exists():
        try:
            previous_count = len(ET.parse(feed_path).getroot().findall('./channel/item'))
        except ET.ParseError:
            previous_count = 0
    if previous_count >= 5 and len(items) < previous_count - 1:
        raise RuntimeError(
            f'Refusing destructive feed shrink: existing feed has {previous_count} episodes, rebuild found {len(items)}'
        )

    cover_img = Image.new('RGB', (1400, 1400), '#0b0f19')
    draw = ImageDraw.Draw(cover_img)
    draw.ellipse((890, 40, 1270, 420), fill='#132f5f')
    draw.ellipse((0, 860, 520, 1380), fill='#3b2315')
    try:
        title_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 116)
        sub_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 54)
    except Exception:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
    draw.text((110, 510), 'FRIDAY AI', fill='#f8fafc', font=title_font)
    draw.text((110, 640), 'Education', fill='#f8fafc', font=title_font)
    draw.text((115, 780), 'Daily operator walkcast', fill='#94a3b8', font=sub_font)
    cover_img.save(PUBLIC / 'cover.png', 'PNG')
    (PUBLIC / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
    (PUBLIC / '.nojekyll').write_text('', encoding='utf-8')

    feed = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:podcast="https://podcastindex.org/namespace/1.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">',
        '<channel>',
        '<title>FRIDAY AI Education Walkcast</title>',
        f'<link>{BASE_URL}/</link>',
        '<language>en-ca</language>',
        '<itunes:author>FRIDAY</itunes:author>',
        '<description>Daily AI education walkcasts for operator-level AI fluency.</description>',
        '<itunes:summary>Daily AI education walkcasts for operator-level AI fluency.</itunes:summary>',
        '<itunes:explicit>false</itunes:explicit>',
        '<itunes:type>episodic</itunes:type>',
        '<itunes:category text="Education"/>',
        f'<itunes:image href="{BASE_URL}/cover.png"/>',
        f'<lastBuildDate>{formatdate(time.time(), usegmt=True)}</lastBuildDate>',
    ]

    for item in reversed(items):
        episode_url = f"{BASE_URL}/{item['mp3_rel']}"
        desc = f"FRIDAY AI Education Episode {item['ep']}: {item['title']}."
        if item['pdf_rel']:
            desc += f" Printable companion: {BASE_URL}/{item['pdf_rel']}"
        guid = f"friday-ai-education-{item['ep']}-{hashlib.sha256(item['mp3_rel'].encode()).hexdigest()[:12]}"
        feed.extend([
            '<item>',
            f'<title>Episode {item["ep"]}: {html.escape(item["title"])}</title>',
            f'<description>{html.escape(desc)}</description>',
            f'<itunes:summary>{html.escape(desc)}</itunes:summary>',
            f'<pubDate>{formatdate(item["mtime"], usegmt=True)}</pubDate>',
            f'<guid isPermaLink="false">{guid}</guid>',
            f'<enclosure url="{episode_url}" length="{item["size"]}" type="audio/mpeg"/>',
            f'<itunes:episode>{int(item["ep"])}</itunes:episode>',
        ])
        if item['duration']:
            feed.append(f'<itunes:duration>{item["duration"]}</itunes:duration>')
        feed.append('</item>')
    feed.extend(['</channel>', '</rss>'])
    feed_path = feed_dir / 'feed.xml'
    feed_path.write_text('\n'.join(feed), encoding='utf-8')
    ET.parse(feed_path)

    index = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta name="viewport" content="width=device-width, initial-scale=1"><title>FRIDAY AI Education Walkcast</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#0b0f19;color:#f8fafc;max-width:760px;margin:6rem auto;padding:0 1.5rem;line-height:1.55}}a{{color:#60a5fa}}code{{background:#111827;padding:.2rem .35rem;border-radius:.25rem}}</style></head><body><h1>FRIDAY AI Education Walkcast</h1><p>Unlisted podcast feed for personal listening.</p><p><strong>RSS feed:</strong><br><a href="/{SECRET_PATH}/feed.xml">/{SECRET_PATH}/feed.xml</a></p><p>Latest episode: {items[-1]['ep'] if items else 'n/a'} · Episodes in feed: {len(items)}</p><p>Add the RSS URL manually in Apple Podcasts or another podcast app.</p></body></html>'''
    (PUBLIC / 'index.html').write_text(index, encoding='utf-8')
    return {
        'episodes': len(items),
        'latest_episode': items[-1]['ep'] if items else None,
        'feed_path': str(feed_path),
        'intended_feed_url': f'{BASE_URL}/{SECRET_PATH}/feed.xml',
    }


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
