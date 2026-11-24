"""Player labels supported by a declaration or a bounded media probe."""
from concurrent.futures import ThreadPoolExecutor, wait
from hashlib import sha256
from time import monotonic, time

from aniplay.providers.scraper import Resolver, ScraperError, mp4_height, quality_label

WAIT_SECONDS = 4.0
MAX_PROBES = 3


def display_quality(value):
    return {'240p': 'SD', '360p': 'SD', '480p': 'SD', '540p': '540p',
            '720p': 'HD', '1080p': 'Full HD', '2160p': '4K'}.get(value, value)


def resolve_choice(resolver, page, kind, value):
    if kind == 'source':
        return resolver._validate(value, page.url, '', value)
    return resolver.get_player(page, value)['stream']


def measure_choice(page, kind, value, deadline):
    remaining = deadline - monotonic()
    if remaining <= 0:
        return ''
    resolver = Resolver(timeout=min(remaining, 2.5))
    resolver.client.dimension_prefix = b''
    original_open = resolver.client.open

    def deadline_open(*args, **kwargs):
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ScraperError('Tempo de medição esgotado.')
        resolver.client.timeout = min(remaining, 2.5)
        return original_open(*args, **kwargs)

    resolver.client.open = deadline_open
    stream = resolve_choice(resolver, page, kind, value)
    if not resolver.verification or resolver.verification[1] != 'video/mp4':
        return ''
    height = mp4_height(resolver, stream)
    return f'{height}p' if height else ''


def player_labels(page, choices, cache):
    labels, pending = [], {}
    now = time()
    for i, (label, kind, value) in enumerate(choices):
        key = 'quality-v2:' + sha256(f'{page.url}\n{kind}\n{value}'.encode()).hexdigest()
        quality = quality_label(label)
        saved = None
        if not quality:
            saved = cache.db.execute('SELECT body,stamp FROM pages WHERE id=? AND stamp>?',
                                     (key, now - 86400)).fetchone()
            quality = saved[0] if saved else ''
        labels.append(quality)
        recent_miss = saved and not quality and saved[1] > now - 120
        if not quality and not recent_miss and len(pending) < MAX_PROBES:
            pending[i] = (key, kind, value)
    if pending and len(choices) > 1:
        deadline = monotonic() + WAIT_SECONDS
        pool = ThreadPoolExecutor(max_workers=2)
        tasks = {pool.submit(measure_choice, page, kind, value, deadline): (i, key)
                 for i, (key, kind, value) in pending.items()}
        try:
            done, _ = wait(tasks, timeout=max(0, deadline - monotonic()))
            for task in done:
                i, _ = tasks[task]
                try:
                    labels[i] = task.result()
                except (OSError, ValueError, ScraperError):
                    labels[i] = ''
            with cache.db:
                cache.db.executemany('INSERT OR REPLACE INTO pages VALUES(?,?,?)',
                                     [(key, time(), labels[i]) for i, key in tasks.values()])
            cache.trim_cache()
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
    return [f'Player {i}: [COLOR yellow]{display_quality(quality)}[/COLOR]' if quality else f'Player {i}'
            for i, quality in enumerate(labels, 1)]
