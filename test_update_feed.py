import tempfile
import unittest
from pathlib import Path
import update_feed


class FeedSafetyTests(unittest.TestCase):
    def test_refuses_destructive_shrink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / 'source'
            public = root / 'public'
            episode = public / 'episodes' / '2026-07-01-ep-001-test'
            episode.mkdir(parents=True)
            (episode / 'episode.mp3').write_bytes(b'not-real-audio')
            feed_dir = public / update_feed.SECRET_PATH
            feed_dir.mkdir(parents=True)
            items = ''.join('<item><title>x</title></item>' for _ in range(10))
            (feed_dir / 'feed.xml').write_text(f'<rss><channel>{items}</channel></rss>')

            old_src, old_public = update_feed.SRC, update_feed.PUBLIC
            update_feed.SRC, update_feed.PUBLIC = src, public
            try:
                with self.assertRaisesRegex(RuntimeError, 'destructive feed shrink'):
                    update_feed.build()
            finally:
                update_feed.SRC, update_feed.PUBLIC = old_src, old_public


if __name__ == '__main__':
    unittest.main()
