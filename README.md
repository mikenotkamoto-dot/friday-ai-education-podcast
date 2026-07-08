# FRIDAY AI Education Podcast Feed

Private-source staging repo for the FRIDAY AI Education Walkcast podcast feed.

## Current state

- Source repo visibility: private
- GitHub Pages: not enabled yet
- Built feed path: `docs/feed-9c7b3d1a4f2e/feed.xml`
- Intended public/unlisted feed URL after Pages is enabled:
  `https://mikenotkamoto-dot.github.io/friday-ai-education-podcast/feed-9c7b3d1a4f2e/feed.xml`

## Privacy truth

GitHub Pages on this account cannot serve a truly private podcast feed from a private repo. The repo can remain private, but the feed URL must be publicly reachable for Apple Podcasts or any standard podcast app to fetch it.

This setup therefore supports **unlisted**, not truly private:

- obscure feed path
- `robots.txt` blocks crawlers
- `noindex,nofollow` meta tag on the landing page
- no submission to Apple/Spotify directories unless explicitly requested

## Update

```bash
cd /Users/emilealbert/FRIDAY/projects/friday-ai-education-podcast
python3 update_feed.py
git add update_feed.py docs
git commit -m "chore: update podcast feed"
git push
```
