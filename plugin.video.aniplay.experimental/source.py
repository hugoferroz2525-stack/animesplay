import hashlib
import html
import json
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request

from aniplay.network import CATALOG_HOST, CLOUD_HOST, TMDB_HOST, PROVIDER_HOSTS, CheckedOpener, media_opener, validate_url

BASE = 'https://bakashi.top'
UA = 'Mozilla/5.0 (Kodi; AniPlay)'
CACHE_BUDGET_BYTES = 20 * 1024 * 1024
PAGE_OPENERS = {host: CheckedOpener(host) for host in (CATALOG_HOST, TMDB_HOST, CLOUD_HOST, *PROVIDER_HOSTS)}
def match(pattern, value, default=''):
    found = re.search(pattern, value, re.I | re.S)
    return html.unescape(found[1]).strip() if found else default

def fetch(url, headers=None, *, host=CATALOG_HOST):
    request = Request(url, headers={'User-Agent': UA, 'Accept':'*/*', **(headers or {})})
    opener = PAGE_OPENERS[host] if host else media_opener
    with opener.open(request, timeout=8) as response:
        return response.read().decode('utf-8', 'replace')

class Cache:
    def __init__(self, path):
        from aniplay.storage.userdata import connect
        self.path = path
        self.user = connect(path)
        self.db = sqlite3.connect(path, timeout=12)
        self.db.execute('CREATE TABLE IF NOT EXISTS pages (id TEXT PRIMARY KEY, stamp REAL, body TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS tmdb_pages (id TEXT PRIMARY KEY, stamp REAL, body TEXT)')
        self.stale = False
        self.last_origin = ''
        self.last_failure = None

    def trim_cache(self):
        """Limita o volume de respostas, sem tocar nos dados de usuário."""
        self.db.execute('CREATE TABLE IF NOT EXISTS cache_maintenance (id INTEGER PRIMARY KEY, stamp REAL)')
        now = time.time()
        with self.db:
            updated = self.db.execute(
                """INSERT INTO cache_maintenance VALUES(1,?)
                   ON CONFLICT(id) DO UPDATE SET stamp=excluded.stamp WHERE stamp<?""",
                (now, now - 300),
            )
            if not updated.rowcount:
                return
            for table in ('pages', 'tmdb_pages'):
                self.db.execute(f"""DELETE FROM {table} WHERE id IN (
                    SELECT id FROM (
                        SELECT id, SUM(length(CAST(body AS BLOB))) OVER (
                            ORDER BY stamp DESC, id ROWS UNBOUNDED PRECEDING
                        ) AS bytes_used FROM {table}
                    ) WHERE bytes_used > ?
                )""", (CACHE_BUDGET_BYTES // 2,))

    def get(self, url, headers=None, ttl=1800, validate=None, request_headers=None, *, host=CATALOG_HOST, cached_only=False):
        self.last_origin = ''
        self.last_failure = None
        if host:
            validate_url(url, host)
        key = hashlib.sha256((url + str(headers)).encode()).hexdigest()
        table = 'tmdb_pages' if host in (TMDB_HOST, CLOUD_HOST) else 'pages'
        old = self.db.execute(f'SELECT stamp,body FROM {table} WHERE id=?', (key,)).fetchone()
        if old and time.time() - old[0] < ttl:
            self.last_origin = 'cache'
            return old[1]
        if cached_only:
            raise ValueError('Página fora do cache.')
        try:
            body = fetch(url, request_headers or headers, host=host)
            if validate:
                validate(body)
            elif url.startswith(BASE) and ('</html>' not in body.lower() or 'Bakashi' not in body):
                raise ValueError('Página do catálogo indisponível')
            if not body.strip():
                raise ValueError('Resposta vazia')
        except (OSError, ValueError) as error:
            self.last_failure = error
            if old:
                self.last_origin = 'cache_antigo'
                self.stale = True
                return old[1]
            raise
        with self.db:
            self.db.execute(f'INSERT OR REPLACE INTO {table} VALUES (?,?,?)', (key, time.time(), body))
        self.trim_cache()
        self.last_origin = 'rede'
        return body

def cards(body, episode=False):
    result = []
    path = 'ep' if episode else '(?:ep|anime)'
    for block in re.findall(r'<article\b.*?</article>', body, re.I | re.S):
        href = match(r'href="([^"]*/' + path + r'/[^"]+)"', block)
        if not href:
            continue
        url = urljoin(BASE, href)
        if episode and not urlsplit(url).path.startswith('/ep/'):
            continue
        name = match(r'<h3[^>]*>(.*?)</h3>', block) or match(r'class="sr-only">Ver ([^<]+)', block)
        num = match(r'Episódio\s*<span[^>]*>([\d.,]+)', block) or match(r'episodio-([\d.]+)$', href)
        result.append(dict(url=url, name=name, num=num, art=match(r'<img[^>]*?\ssrc="([^"]+)', block), plot=match(r'<p[^>]*>(.*?)</p>', block)))
    return result

def episode_list(cache, body, kind, count_only=False):
    endpoint = match(r"var endpoint = '([^']+)'", body)
    season = match(r"season:\s*'(\d+)'", body)
    if not endpoint:
        rows = cards(body, True)
        return len(rows) if count_only else rows
    canonical = match(r'<link rel="canonical" href="([^"]+)', body, BASE)
    ajax = {'X-Requested-With': 'XMLHttpRequest'}
    headers = dict(ajax, Accept='application/json', Referer=canonical)

    def page_url(page):
        params = dict(type=kind, page=page, per_page=50, order='asc')
        if season:
            params['season'] = season
        return urljoin(BASE, endpoint) + '?' + urlencode(params)

    def read_page(db, page):
        return json.loads(db.get(page_url(page), ajax, validate=json.loads, request_headers=headers))

    snapshot_key = canonical + '\n' + page_url(1)
    cache.db.execute("""CREATE TABLE IF NOT EXISTS episode_snapshots (
        id TEXT PRIMARY KEY, signature TEXT, stamp REAL, entries TEXT)""")
    saved = cache.db.execute('SELECT signature,stamp,entries FROM episode_snapshots WHERE id=?',
                             (snapshot_key,)).fetchone()
    try:
        first = read_page(cache, 1)
    except OSError:
        if not saved:
            raise
        cache.stale = True
        entries = json.loads(saved[2])
        return len(entries) if count_only else entries
    if count_only:
        return int(first['total'])
    last_page = int(first['last_page'])
    if last_page <= 1:
        return cards(first['html'], True)
    signature = hashlib.sha256((body + json.dumps(first, sort_keys=True)).encode()).hexdigest()
    if saved and saved[0] == signature and time.time() - saved[1] < 1800:
        return json.loads(saved[2])

    def read_remaining(page):
        db = Cache(cache.path)
        try:
            data = read_page(db, page)
            return cards(data['html'], True), db.stale
        finally:
            db.user.close()
            db.db.close()

    items = {entry['url']: entry for entry in cards(first['html'], True)}
    try:
        # Limit pending pages so a rate limit stops the remaining requests promptly.
        with ThreadPoolExecutor(max_workers=4) as pool:
            for start in range(2, last_page + 1, 4):
                batch = range(start, min(start + 4, last_page + 1))
                for entries, stale in pool.map(read_remaining, batch):
                    items.update((entry['url'], entry) for entry in entries)
                    cache.stale |= stale
    except OSError:
        if not saved:
            raise
        cache.stale = True
        return json.loads(saved[2])
    entries = list(items.values())
    if not cache.stale:
        with cache.db:
            cache.db.execute('INSERT OR REPLACE INTO episode_snapshots VALUES(?,?,?,?)',
                             (snapshot_key, signature, time.time(), json.dumps(entries, ensure_ascii=False)))
    return entries


def player_page(body):
    if not re.search(r'videoUrl|videoSources|<source|file["\']?\s*:', body):
        raise ValueError('Player indisponível')

def media(frame, ref, cache=None):
    headers = {'Referer': ref}
    body = (cache.get(frame, headers, ttl=120, validate=player_page, host=None)
            if cache else fetch(frame, headers, host=None))
    packed = re.search(r"\}\('([^']*)',(\d+),\d+,'([^']*)'\.split", body)
    if packed:
        words = packed[3].split('|')
        digits = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        def decode(token):
            value = 0
            for ch in token[0]:
                if ch not in digits[:int(packed[2])]:
                    return token[0]
                value = value * int(packed[2]) + digits.index(ch)
                if value >= len(words):
                    return token[0]
            return words[value] or token[0]
        body += re.sub(r'\b[0-9A-Za-z]+\b', decode, packed[1])
    body = re.sub(r'\\+/', '/', body)
    path = match(r'["\']videoUrl["\']\s*:\s*["\']([^"\']+)', body) or match(r'(?:file["\']?\s*:|<source[^>]*src=)\s*["\']([^"\']+)', body)
    url = urljoin(frame, path)
    if not path or urlsplit(url).scheme not in ('http','https'):
        raise ValueError('Fonte de vídeo indisponível')
    markers = re.search(r'"intro"\s*:\s*\{\s*"start"\s*:\s*([\d.]+)\s*,\s*"end"\s*:\s*([\d.]+)', body)
    return url, tuple(map(float, markers.groups())) if markers else ()

def player_buttons(body, page_url):
    for attrs, content in re.findall(r'<button\b([^>]*)>(.*?)</button>', body, re.I | re.S):
        url = match(r"""\bdata-url=["']([^"']+)""", attrs)
        if url:
            label = re.sub('<[^>]+>', ' ', html.unescape(content)).strip()
            audio = 'Dublado' if 'dublad' in label.casefold() else (
                'Legendado' if 'legendad' in label.casefold() else 'Áudio não informado')
            yield audio, label, urljoin(page_url, url)


def audio_sources(body, page_url):
    groups = {}
    for audio, _, frame in player_buttons(body, page_url):
        group = groups.setdefault(audio, [])
        if frame not in group:
            group.append(frame)
    frame = match(r'''<iframe\b[^>]*\bsrc=["']([^"']+)''', body)
    if frame:
        frame = urljoin(page_url, frame)
        if all(frame not in group for group in groups.values()):
            groups.setdefault('Áudio não informado', []).append(frame)
    return groups

def recent_searches(db, term=''):
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS searches (id INTEGER PRIMARY KEY, term TEXT, normalized TEXT UNIQUE)')
        if term:
            db.execute('INSERT OR REPLACE INTO searches(term,normalized) VALUES (?,?)',(term,term.casefold()))
            db.execute('DELETE FROM searches WHERE id NOT IN (SELECT id FROM searches ORDER BY id DESC LIMIT 30)')
        return [row[0] for row in db.execute('SELECT term FROM searches ORDER BY id DESC')]

def filter_options(body, field):
    options = match(r'<select[^>]*id="'+field+r'Filter"[^>]*>(.*?)</select>', body)
    rows = [(value,html.unescape(label.strip())) for value,label in re.findall(r'<option\s+value="([^"]+)"[^>]*>([^<]+)',options)]

    if field != 'genre':
        return list(dict.fromkeys(rows))
    aliases = dict(action='acao', adventure='aventura', comedy='comedia', fantasy='fantasia',
                   historical='historico', military='militar', mystery='misterio', psychological='psicologico',
                   school='vida-escolar', sports='esportes', supernatural='sobrenatural', vampire='vampiros',
                   thriller='suspense')
    aliases['sci-fi'] = 'ficcao-cientifica'
    labels = dict(rows)
    groups = {}
    for value, label in rows:
        key = aliases.get(value, value)
        groups.setdefault(key, []).append(value)
    return sorted(((','.join(dict.fromkeys(values)), labels.get(key, labels[values[0]]))
                   for key, values in groups.items()), key=lambda row: row[1].casefold())
