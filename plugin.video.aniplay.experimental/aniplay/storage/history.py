"""Keep progress by episode page, independent of the current media URL."""
import hashlib
import json
import math
import re
from urllib.parse import urlsplit
import sqlite3
import time
from contextlib import closing
from pathlib import Path

PENDING = 'AniPlay.PendingPlayback'
FIELDS = ('id', 'url', 'title', 'showtitle', 'episode_title', '_tmdb_title', 'show_url', 'icon', 'episode',
          'showid', 'local', 'raw', 'season', 'movie_id', 'show_title', 'provider', 'mediatype', 'audio', '_alternate_parents', 'tmdb_id', '_display_season', '_tmdb_season', '_tmdb_episode', '_season_mapped')


def media_key(path):
    url = path.split('|', 1)[0]
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


def public_episode(item):
    result={key: item[key] for key in FIELDS if key in item and key!='_alternate_parents'}
    return result


def show_key(item, episode_id):
    from aniplay.tmdb_match import slug

    if item.get('show_url'):
        return slug(item['show_url'])
    stem = urlsplit(item.get('url') or episode_id).path.rstrip('/').rsplit('/', 1)[-1]
    match = re.fullmatch(r'(.+)-\d+-episodio-[\d.,]+', stem)
    return match[1] if match else ''


class History:
    def __init__(self, profile):
        profile = Path(profile)
        profile.mkdir(parents=True, exist_ok=True)
        self.path = profile / 'watch-history-v1.db'
        with closing(self.connect()) as conn, conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS episodes(
                id TEXT PRIMARY KEY, item TEXT NOT NULL, position REAL NOT NULL,
                duration REAL NOT NULL, watched INTEGER NOT NULL, updated REAL NOT NULL
            )''')

            if conn.execute('PRAGMA user_version').fetchone()[0] == 0:
                conn.execute('BEGIN IMMEDIATE')
                if conn.execute('PRAGMA user_version').fetchone()[0] == 0:
                    conn.execute("ALTER TABLE episodes ADD COLUMN show_key TEXT NOT NULL DEFAULT ''")
                    conn.execute('ALTER TABLE episodes ADD COLUMN in_progress INTEGER NOT NULL DEFAULT 0')
                    for ident, raw in conn.execute('SELECT id,item FROM episodes'):
                        try:
                            key = show_key(json.loads(raw), ident)
                        except (ValueError, TypeError, AttributeError):
                            key = ''
                        conn.execute('UPDATE episodes SET show_key=?, in_progress=1-watched WHERE id=?',
                                     (key, ident))
                    conn.execute('CREATE INDEX episodes_show ON episodes(show_key, watched)')
                    conn.execute('PRAGMA user_version=1')

    def connect(self):
        return sqlite3.connect(str(self.path), timeout=1)

    def save(self, item, position, duration, ended=False):
        if not all(math.isfinite(value) for value in (position, duration)):
            return
        if duration < 1 or position < 0:
            return
        position = min(position, duration)
        watched = position >= duration * 0.90 or (ended and position >= duration * 0.85)
        if not watched and position < 10:
            return
        with closing(self.connect()) as conn, conn:
            conn.execute("""INSERT INTO episodes(id,item,position,duration,watched,updated,show_key,in_progress)
                         VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                         item=excluded.item, position=excluded.position, duration=excluded.duration,
                         watched=max(episodes.watched,excluded.watched), updated=excluded.updated,
                         show_key=coalesce(nullif(excluded.show_key,''),episodes.show_key),
                         in_progress=excluded.in_progress""",
                         (item['id'], json.dumps(public_episode(item), ensure_ascii=False), position,
                          duration, int(watched), time.time(), show_key(item, item['id']), int(not watched)))

    def watched_for_show(self, show_url):
        from aniplay.tmdb_match import slug
        with closing(self.connect()) as conn:
            return {row[0] for row in conn.execute(
                'SELECT id FROM episodes WHERE show_key=? AND watched=1', (slug(show_url),))}

    def progress_for(self, ids):
        ids = list(dict.fromkeys(ids))
        progress = {}
        with closing(self.connect()) as conn:
            for offset in range(0, len(ids), 500):
                batch = ids[offset:offset + 500]
                marks = ','.join('?' for _ in batch)
                rows = conn.execute(f'SELECT id,position,duration,watched,in_progress FROM episodes WHERE id IN ({marks})', batch)
                progress.update((row[0], row[1:]) for row in rows)
        return progress

    def resume(self, episode_id):
        with closing(self.connect()) as conn:
            result = conn.execute('SELECT position FROM episodes WHERE id=? AND in_progress=1',
                                  (episode_id,)).fetchone()
        return result[0] if result else 0

    def unfinished(self):
        with closing(self.connect()) as conn:
            return [(json.loads(item), position) for item, position in conn.execute(
                'SELECT item,position FROM episodes WHERE in_progress=1 ORDER BY updated DESC LIMIT 100')]

    def recently_watched(self):
        with closing(self.connect()) as conn:
            return [json.loads(row[0]) for row in conn.execute(
                'SELECT item FROM episodes WHERE watched=1 ORDER BY updated DESC LIMIT 100')]
