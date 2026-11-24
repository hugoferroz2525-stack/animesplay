"""Complemento local ao índice distribuído no ZIP."""
import re
import time
from aniplay.tmdb_match import slug, index
from aniplay.runtime import cache
from source import BASE, cards


def rows():
    cache.db.execute('CREATE TABLE IF NOT EXISTS catalog_updates (slug TEXT PRIMARY KEY,title TEXT,url TEXT,art TEXT,kind TEXT,id INTEGER)')
    return cache.db.execute('SELECT slug,title,url,art,kind,id FROM catalog_updates').fetchall()


def record(entries, metadata):
    rows()
    with cache.db:
        for entry,data in zip(entries,metadata):
            key=slug(entry['url'])
            if key not in index():
                cache.db.execute('''INSERT INTO catalog_updates VALUES(?,?,?,?,?,?)
                    ON CONFLICT(slug) DO UPDATE SET title=excluded.title,url=excluded.url,art=excluded.art,
                    kind=coalesce(excluded.kind,kind),id=coalesce(excluded.id,id)''',
                    (key,entry['name'],entry['url'],entry['art'],data.get('media_type'),data.get('id')))


def refresh():
    from aniplay.metadata import lookup
    cache.db.execute('CREATE TABLE IF NOT EXISTS catalog_cursor (id INTEGER PRIMARY KEY,page INTEGER,due REAL)')
    page,due=cache.db.execute('SELECT page,due FROM catalog_cursor WHERE id=1').fetchone() or (1,0)
    if time.time()<due:
        return
    for _ in range(4):
        url = BASE + '/lista-de-animes'
        if page > 1:
            url += '?page=' + str(page)
        try:
            body = cache.get(url)
        except (OSError, ValueError) as exc:
            import xbmc
            xbmc.log('AniPlay: atualização do catálogo adiada: ' + type(exc).__name__, xbmc.LOGWARNING)
            with cache.db:
                cache.db.execute('INSERT OR REPLACE INTO catalog_cursor VALUES(1,?,?)', (page,time.time()+300))
            return
        entries=cards(body)
        if not entries or cache.stale:
            return
        metadata=[{} if slug(e['url']) in index() else lookup(e['name'],cache,e['url']) for e in entries]
        record(entries,metadata)
        more=any(int(n)>page for n in re.findall(r'data-page="(\d+)"',body)) or 'rel="next"' in body
        page=page+1 if more else 1
        with cache.db:
            cache.db.execute('INSERT OR REPLACE INTO catalog_cursor VALUES(1,?,?)',(page,time.time()+(60 if more else 21600)))
        if not more:
            break
