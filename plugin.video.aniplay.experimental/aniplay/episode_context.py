"""Associa episódios ao TMDB e reutiliza os metadados da temporada."""
import json
import re
import time
from urllib.parse import urlsplit

from aniplay.menu_metadata import catalog
from aniplay.runtime import addon, cache

FIELDS = ('showid', 'season', 'local', 'raw', 'show_url', 'show_title', 'episode_title', 'movie_id')


def remember(params, data, cast, fan):
    values = {key: str(params[key]) for key in FIELDS if params.get(key) not in ('', None)}
    if values.get('showid') or values.get('movie_id'):
        values['_snapshot'] = dict(data=data, cast=cast, fan=fan, stamp=time.time(),
                                   language=addon.getSetting('tmdb_language') or 'pt-BR')
        cache.db.execute('CREATE TABLE IF NOT EXISTS episode_links(url TEXT PRIMARY KEY, metadata TEXT)')
        cache.db.execute('INSERT OR REPLACE INTO episode_links VALUES (?,?)',
                         (params['url'], json.dumps(values)))


def cached(params, *, include_stale=False):
    if params.get('source_order'):
        return None
    cache.db.execute('CREATE TABLE IF NOT EXISTS episode_links(url TEXT PRIMARY KEY, metadata TEXT)')
    row = cache.db.execute('SELECT metadata FROM episode_links WHERE url=?', (params['url'],)).fetchone()
    if not row:
        return None
    stored = json.loads(row[0])
    snapshot = stored.pop('_snapshot', {})
    if any(params.get(key) and stored.get(key) and str(params[key]) != stored[key]
           for key in ('showid', 'movie_id', 'season', 'local')):
        return None
    params.update(stored)
    ttl = 86400 * (addon.getSettingInt('tmdb_days') or 7)
    if snapshot.get('language') == (addon.getSetting('tmdb_language') or 'pt-BR'):
        if not snapshot.get('data', {}).get('id'):
            ttl = min(ttl, 300)
        fresh = time.time() - snapshot.get('stamp', 0) < ttl
        if fresh or include_stale:
            return {**snapshot, 'stale': not fresh}
    return {}


def restore(params):
    if params.get('source_order'):
        return {}
    snapshot = cached(params)
    if snapshot:
        return snapshot
    from aniplay.metadata import details, season_details
    if str(params.get('movie_id', '')).isdigit():
        movie = details('movie', params['movie_id'], cache, full=True, cached_only=True)
        return {'data': movie} if movie else {}
    if all(str(params.get(key, '')).isdigit() for key in ('showid', 'season', 'local')):
        season = season_details(params['showid'], params['season'], cache, cached_only=True)
        episode = next((entry for entry in season.get('episodes', [])
                        if str(entry.get('episode_number')) == str(params['local'])), None)
        return {'data': episode, 'cast': season.get('credits', {}).get('cast')} if episode else {}
    match = re.fullmatch(r'/ep/(.+)-(\d+)-episodio-(\d+)/?', urlsplit(params['url']).path)
    record = catalog()[0].get(match[1]) if match else None
    if not record:
        return {}
    from aniplay.catalog import series
    resolved = series(record[1], target=params['url'], preferred_season=match[2])
    if not resolved:
        return {}
    values, data, cast, fan = resolved
    params.update({key: str(values[key]) for key in FIELDS if values.get(key) not in ('', None)})
    with cache.db:
        remember(params, data, cast, fan)
    return dict(data=data, cast=cast, fan=fan)
