"""Busca agrupada e navegação por fonte no AniPlay."""
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from time import monotonic, time
from urllib.parse import urlencode, urlsplit
import xbmcgui

from source import BASE, Cache, cards
from aniplay.flix_ui import notification
from aniplay.episode_order import flat_season_position, flat_season_ranges
from aniplay.metadata import lookup, season_details
from aniplay.network import RedirectRejected, validate_url
from urllib.error import HTTPError, URLError
from aniplay.providers.catalog import FONTES, extrair_animes, extrair_episodios
from aniplay.providers.grouping import agrupar_animes, chave_titulo, identity
from aniplay.providers.editions import (
    COSMOS, COSMOS_FILMS, ONE_PIECE, SEGMENTS, companion_segment, provider_slug,
    reference as provider_reference,
)
from aniplay.providers.scraper import Document, http_url, next_page
from aniplay.runtime import cache, database, handle, profile, q
from aniplay.storage.history import History
from aniplay.titles import clean_text, episode_title, season_title
from aniplay.views import item, yellow
import xbmc
import xbmcplugin

SOURCES = {name: (base, kind) for name, base, kind in (('Bakashi', BASE, 'bakashi'), *FONTES)}
HOSTS = {name: urlsplit(base).hostname for name, (base, _) in SOURCES.items()}
MAX_SEARCH_PAGES = 12
MAX_EPISODE_PAGES = 150


def check_source(site, url):
    if site not in HOSTS:
        raise ValueError('Servidor desconhecido.')
    validate_url(url, HOSTS[site])


def page(db, site, url):
    check_source(site, url)
    return db.get(url, host=HOSTS[site])


def source_log(site, stage, started, origin='', items=0, error=None):
    fields = [f'fonte={site}', f'etapa={stage}', f'tempo_ms={round((monotonic() - started) * 1000)}']
    if origin:
        fields.extend((f'origem={origin}', f'itens={items}'))
    if isinstance(error, RedirectRejected):
        fields.extend((f'http={error.status}', f'destino={error.destination}', 'resultado=redirecionamento_recusado'))
    elif isinstance(error, HTTPError):
        fields.extend((f'http={error.code}', 'resultado=erro_http'))
    elif error:
        reason = error.reason if isinstance(error, URLError) else error
        fields.append(f'resultado={type(reason).__name__}')
    elif origin:
        fields.append('resultado=ok' if items else 'resultado=sem_itens_reconhecidos')
    xbmc.log('[AniPlay/Fontes] ' + ' '.join(fields), xbmc.LOGWARNING if error else xbmc.LOGINFO)


def search_source(site, term):
    origin, kind = SOURCES[site]
    query = {'hinata': 'busca', 'anitube': 's', 'bakashi': 'search'}[kind]
    path = '/lista-de-animes' if kind == 'bakashi' else '/busca' if term else '/'
    address = origin + path + ('?' + urlencode({query: term}) if term else '')
    found, visited = [], set()
    deadline = monotonic() + 12
    db = Cache(database)
    started = monotonic()
    stage = 'busca' if term else 'catalogo'
    try:
        while (address and address not in visited and len(visited) < MAX_SEARCH_PAGES
               and monotonic() < deadline):
            visited.add(address)
            started = monotonic()
            html = page(db, site, address)
            if kind == 'bakashi':
                entries = [(row['name'], row['url'], row['art']) for row in cards(html)]
            else:
                entries = extrair_animes(html, address, kind)
            source_log(site, stage, started, db.last_origin, len(entries), db.last_failure)
            for name, url, image in entries:
                try:
                    check_source(site, url)
                except ValueError:
                    continue
                if urlsplit(url).path not in ('', '/'):
                    found.append((site, clean_text(name), url, image))
            address = next_page(Document(html).root, address)[0] if term and entries else ''
    except (OSError, ValueError) as error:
        source_log(site, stage, started, error=error)
        return found, site if not found else ''
    finally:
        db.user.close()
        db.db.close()
    return found, ''


def grouped(rows):
    from aniplay.tmdb_match import index, slug
    mapping = index()
    ids = {}
    for site, _, url, _ in rows:
        ref = mapping.get(slug(url)) if site == 'Bakashi' else provider_reference(url)
        if ref:
            ids[url] = f'{ref[0]}:{ref[1]}'
    return agrupar_animes(rows, ids)


def encode(rows):
    return json.dumps(rows, ensure_ascii=False, separators=(',', ':'))


def representative(group):
    return min(group.fontes, key=lambda row: (row['site'] != 'Bakashi', row['season'] or 1, bool(row['audio'])))


def show_groups(groups, fallback=None, metadata=None):
    from aniplay.catalog import catalog_metadata
    fallback = fallback or {}
    primary = [representative(g) for g in groups]
    entries = [{'url': src['url'], 'name': src['title']} for src in primary]
    if metadata is None:
        metadata = {row['url']: data for row, data in zip(entries, catalog_metadata(entries))}
    for group, src in zip(groups, primary):
        data = metadata.get(src['url'], {}) or fallback.get(src['url'], {})
        title = group.titulo
        if data.get('media_type') in ('tv', 'movie') and data.get('name'):
            title = identity(data['name'], '')[0]
        art = src['imagem'] or next((r['imagem'] for r in group.fontes if r['imagem']), '')
        params = dict(title=title, art=art, sources=encode(group.fontes))
        params['url'] = src['url']
        item(title, 'multi_servers', params, data, art,
             info=dict(title=title, mediatype='movie' if data.get('media_type') == 'movie' else 'tvshow',
                       plot=data.get('overview') or fallback.get(src['url'], {}).get('overview', '')))


def query_sources(term, sites):
    with ThreadPoolExecutor(max_workers=len(sites)) as workers:
        lists = list(workers.map(lambda site: search_source(site, term), sites))
    return [row for rows, _ in lists for row in rows], [site for _, site in lists if site]


def browse():
    from aniplay.data_files import load
    term = q.get('term', '').strip()
    rows, unavailable = query_sources(term, tuple(SOURCES))
    if not term:
        rows.extend(('Bakashi', name, url, art) for name, url, art in load('catalog-links.json').values())
    groups = grouped(rows)
    page_number = max(1, int(q.get('page', '1')))
    start = (page_number - 1) * 25
    show_groups(groups[start:start + 25])
    if start + 25 < len(groups):
        item('Próxima página', 'query' if term else 'catalog', dict(term=term, page=page_number + 1), icon='next')
    if unavailable and page_number == 1:
        notification('Sem resposta de ' + ', '.join(unavailable), 'Catálogo', 'alert')
    return bool(groups)


def expand(sources):
    from aniplay.data_files import load
    rows = [(s['site'], s['title'], s['url'], s.get('imagem', '')) for s in sources]
    known_urls = {s['url'] for s in sources}
    key = next((g.key for g in grouped(rows)), '')
    names = {chave_titulo(identity(s['title'], s['url'])[0]) for s in sources}
    candidates = [('Bakashi', name, url, art) for name, url, art in load('catalog-links.json').values()]
    local_groups = grouped(candidates)
    aliases = [group for group in local_groups if chave_titulo(group.titulo) in names]
    alias_key = aliases[0].key if key.startswith('title:') and len(aliases) == 1 else None
    for group in local_groups:
        if group.key in (key, alias_key) or any(src['url'] in known_urls for src in group.fontes):
            rows.extend((s['site'], s['title'], s['url'], s['imagem']) for s in group.fontes)
            names.update(chave_titulo(identity(s['title'], s['url'])[0]) for s in group.fontes)
    extra, _ = query_sources(identity(sources[0]['title'], sources[0]['url'])[0], tuple(SOURCES)[1:])
    rows.extend(row for row in extra if chave_titulo(identity(row[1], row[2])[0]) in names)
    unique = {}
    for site, title, url, art in rows:
        check_source(site, url)
        _, audio, season = identity(title, url)
        unique.setdefault((site, url), dict(site=site, title=title, url=url, imagem=art,
                                            audio=audio, season=season))
    order = {site: i for i, site in enumerate(SOURCES)}
    return sorted(unique.values(), key=lambda row: order[row['site']])


def servers():
    from aniplay.catalog import catalog_metadata
    sources = json.loads(q['sources'])
    if not isinstance(sources, list) or not sources:
        raise ValueError('Lista de servidores inválida.')
    selected_audio = q.get('edition')
    if selected_audio == 'unknown':
        selected_audio = ''
    if selected_audio is None:
        sources = expand(sources)
    else:
        for source in sources:
            check_source(source['site'], source['url'])
    bk = next((s for s in sources if s['site'] == 'Bakashi'), None)
    data = (catalog_metadata([{'url': bk['url'], 'name': q['title']}])[0] if bk
            else lookup(q['title'], cache, sources[0]['url'], full=True))
    xbmcplugin.setPluginCategory(handle, q['title'])
    languages = ('Dublado', 'Legendado', '')
    available = {source.get('audio', '') for source in sources}
    if selected_audio is None and len(available) > 1:
        for language in languages:
            if language not in available:
                continue
            caption = language or 'Áudio não informado'
            item(yellow(caption), 'multi_servers',
                 dict(title=q['title'], art=q.get('art', ''), sources=encode(sources),
                      edition=language or 'unknown'), data, q.get('art', ''), icon='season',
                 info=dict(title=yellow(caption), sorttitle=caption, mediatype='tvshow'))
        return
    providers = {}
    for source in sources:
        if selected_audio is None or source.get('audio', '') == selected_audio:
            providers.setdefault(source['site'], []).append(source)
    for number, (site, rows) in enumerate(providers.items(), 1):
        label = f'Servidor {number}'
        art = rows[0].get('imagem') or q.get('art', '')
        values = dict(site=site, url=rows[0]['url'], title=q['title'],
                      sources=encode(rows), bakashi=bk['url'] if bk else '', art=art, server=label)
        if site == 'Bakashi' and selected_audio:
            values['preferred_audio'] = selected_audio
        item(yellow(label), 'multi_seasons', values,
             data, art, icon='season', info=dict(title=yellow(label), sorttitle=label, tvshowtitle=q['title'],
                                        mediatype='movie' if data.get('media_type') == 'movie' else 'tvshow'),
             server_badge=label)


def episode_numbers(title, url):
    path = urlsplit(url).path
    label = clean_text(title)
    pair = re.search(r'\bS(\d+)\s*E(\d+(?:[.,]\d+)?)\b', label, re.I)
    if not pair:
        pair = re.search(r'(?:^|[/_-])S(\d+)E(\d+(?:[.,]\d+)?)(?:$|[/_-])', path, re.I)
    if pair:
        return int(pair[1]), Decimal(pair[2].replace(',', '.'))
    season = re.search(r'\b(?:temporada|season)\s+(\d+)\b', label, re.I)
    if not season:
        season = re.search(r'/(?:season|temporada)[-/](\d+)(?:/|$)', path, re.I)
    number = re.search(r'\b(?:ep\.?|epis[oó]dio|episode)\s*[-:#]?\s*(\d+(?:[.,]\d+)?)\b', label, re.I)
    if not number:
        number = re.fullmatch(r'(\d+(?:[.,]\d+)?)', label)
    if not number:
        number = re.search(r'[-/](?:ep|episodio|episode)[-/]?(\d+(?:[.,]\d+)?)/?$', path, re.I)
    return (int(season[1]) if season else None,
            Decimal(number[1].replace(',', '.')) if number else None)


def group_episodes(entries, show, *, separate_reused=False):
    numbered = [(title, url, art, *episode_numbers(title, url)) for title, url, art in entries]
    explicit = any(s is not None for _, _, _, s, _ in numbered)
    counts = Counter(row[-1] for row in numbered if row[-1] is not None)
    numbers = counts if separate_reused else (row[-1] for row in numbered)
    ranges = flat_season_ranges(show.get('seasons', []), numbers, allow_gaps=True) if not explicit else []
    buckets = {}
    for title, url, art, season, number in numbered:
        local = number
        if separate_reused and (number is None or counts[number] > 1 or not ranges):
            season = -1
        elif ranges:
            season, local = flat_season_position(ranges, number)
        if season is None:
            season = -1 if explicit else 1
        buckets.setdefault(season, []).append((title, url, art, local, number))
    for rows in buckets.values():
        rows.sort(key=lambda row: (row[3] is None, row[3] or 0))
    return dict(sorted(buckets.items(), key=lambda pair: (pair[0] < 0, pair[0])))


def load_episodes(site, url):
    snapshot_key = 'provider-episodes-v1:' + url
    saved = cache.db.execute('SELECT body FROM pages WHERE id=? AND stamp>?', (snapshot_key, time()-1800)).fetchone()
    if saved:
        return json.loads(saved[0])
    complete = True
    kind = SOURCES[site][1]
    entries, visited = {}, set()
    while url and url not in visited and len(visited) < MAX_EPISODE_PAGES:
        visited.add(url)
        started = monotonic()
        try:
            rows, url, _ = extrair_episodios(page(cache, site, url), url, kind)
            complete = complete and not cache.last_failure
            source_log(site, 'episodios', started, cache.last_origin, len(rows), cache.last_failure)
        except (OSError, ValueError) as error:
            source_log(site, 'episodios', started, error=error)
            if not entries:
                raise
            notification('Parte da lista de episódios está indisponível.', site, 'alert')
            break
        for row in rows:
            try:
                check_source(site, row[1])
            except ValueError:
                continue
            entries.setdefault(row[1], row)
    if url and len(visited) == MAX_EPISODE_PAGES:
        notification('A lista atingiu o limite de páginas.', site, 'alert')
    result = list(entries.values())
    if result and complete and not url:
        with cache.db:
            cache.db.execute('INSERT OR REPLACE INTO pages VALUES(?,?,?)', (snapshot_key, time(), encode(result)))
        cache.trim_cache()
    return result


def server_rows():
    site = q['site']
    sources = json.loads(q['sources']) if q.get('sources') else [
        dict(site=site, url=q['url'], title=q.get('source_title', q.get('title', '')), audio='', season=None)]
    for row in sources:
        if row['site'] != site:
            raise ValueError('Fonte fora do servidor escolhido.')
        check_source(site, row['url'])
    return sorted(sources, key=lambda row: (row.get('season') or 1, bool(row.get('audio'))))


def bakashi_seasons(sources):
    from aniplay.catalog import series
    shown = set()
    routing = encode(sources) if len(sources) > 1 else ''
    xbmcplugin.setPluginCategory(handle, q.get('title', ''))
    for row in sources:
        try:
            series(row['url'], server_sources=routing, seen_seasons=shown,
                   season_hint=row.get('season'))
        except (OSError, ValueError):
            continue


def provider_season_sources(sources):
    expanded = {src['url']: src for src in sources}
    for src in sources:
        companion = companion_segment(src['url'])
        if companion and companion not in expanded:
            check_source(src['site'], companion)
            expanded[companion] = dict(src, url=companion, season=None)
        try:
            root = Document(page(cache, src['site'], src['url'])).root
        except (OSError, ValueError):
            continue
        original = chave_titulo(identity(src['title'], src['url'])[0])
        for anchor in root.find_all('a'):
            link = http_url(anchor.attrs.get('href'), src['url'])
            if not link or link in expanded or re.match(r'/videos?/', urlsplit(link).path):
                continue
            label = anchor.text()
            header = re.fullmatch(r'(?:temporada|season)\s+(\d+)', label, re.I)
            base, _, number = identity(label, link)
            if header:
                number = int(header[1])
            elif not number or chave_titulo(base) != original:
                continue
            if urlsplit(link).path == urlsplit(src['url']).path and not urlsplit(link).query:
                continue
            try:
                check_source(src['site'], link)
            except ValueError:
                continue
            expanded[link] = dict(src, url=link, season=number)
    return list(expanded.values())


def variant_rows(sources, data):
    buckets = {}
    for src in sources:
        try:
            entries = load_episodes(src['site'], src['url'])
        except (OSError, ValueError):
            continue
        hint = src.get('season')
        slug = provider_slug(src['url'])
        segment = SEGMENTS.get(slug)
        assigned = group_episodes(entries, {} if hint or segment else data,
                                  separate_reused=slug in ONE_PIECE and not hint)
        for season, rows in assigned.items():
            season = hint if season == 1 and hint else season
            for name, link, art, local, raw in rows:
                target_season = season
                if segment:
                    _, tmdb_season, offset, count = segment
                    if raw is not None and raw == int(raw) and 1 <= raw <= count:
                        target_season, local = tmdb_season, raw + offset
                    else:
                        target_season = -1
                key = local if local is not None else link
                target = buckets.setdefault(target_season, {}).setdefault(key, [])
                if not any(candidate['url'] == link for candidate in target):
                    target.append(dict(name=name, url=link, art=art, local=str(local) if local is not None else '',
                                       raw=str(raw) if raw is not None else '', audio=src.get('audio', ''),
                                       parent=src['url']))
    result = {}
    for season, rows in sorted(buckets.items(), key=lambda x: (x[0] < 0, x[0])):
        result[season] = []
        for key in sorted(rows, key=lambda key: (isinstance(key, str), key)):
            options = rows[key]
            # If an edition has more than one record, the number alone cannot pair editions.
            if len({option['audio'] for option in options}) != len(options):
                result[season].extend([option] for option in options)
            else:
                result[season].append(options)
    return result


def cosmos_films(sources, title, art):
    from aniplay.metadata import details
    from aniplay.episode_context import remember
    for src in sources:
        if provider_slug(src['url']) != COSMOS:
            continue
        for name, url, thumbnail in load_episodes(src['site'], src['url']):
            _, number = episode_numbers(name, url)
            ident = COSMOS_FILMS.get(number)
            if not ident:
                continue
            data = details('movie', ident, cache, full=True) or {'id': ident, 'media_type': 'movie'}
            heading = data.get('name') or f'{title} · Parte {number}'
            params = dict(url=url, provider=src['site'], show_url=src['url'], title=heading,
                          episode_title=heading, movie_id=ident, art=thumbnail or art)
            with cache.db:
                remember(params, data, None, '')
            yield heading, params, data


def export_provider():
    from aniplay.export import write_episode
    sources = json.loads(q['sources'])
    site = next(row['site'] for row in sources if row['url'] == q['url'])
    q['site'] = site
    q['sources'] = encode([row for row in sources if row['site'] == site])
    rows = server_rows()
    if rows and all(provider_slug(row['url']) == COSMOS for row in rows):
        from aniplay.export import write_movie
        films = list(cosmos_films(rows, q['title'], q.get('art', '')))
        for heading, params, _ in films:
            write_movie(heading, params)
        return len(films)
    data = lookup(q['title'], cache, q['url'], full=True)
    groups = variant_rows(provider_season_sources(server_rows()), data)
    count = 0
    for season, episodes in groups.items():
        for options in episodes:
            row = options[0]
            params = dict(url=row['url'], provider=site, show_url=row['parent'], show_title=q['title'],
                          season=season, raw=row['raw'], local=row['local'], art=row['art'], title=row['name'])
            if data.get('media_type') == 'tv':
                params['showid'] = data['id']
            languages = audio_variants(options)
            if len(languages) > 1:
                params['audio_options'] = encode(languages)
            write_episode(q['title'], params, max(0, season), row['local'])
            count += 1
    return count


def audio_variants(options):
    audio = {}
    for option in options:
        language = option['audio'] or 'Áudio não informado'
        audio.setdefault(language, dict(option, audio=language))
    return list(audio.values())


def seasons():
    sources = server_rows()
    site = q['site']
    if site == 'Bakashi':
        bakashi_seasons(sources)
        return
    if sources and all(provider_slug(src['url']) == COSMOS for src in sources):
        for heading, params, data in cosmos_films(sources, q['title'], q.get('art', '')):
            item(heading, 'play', params, data, params['art'], icon='episode')
        return
    bk = q.get('bakashi', '')
    if bk:
        check_source('Bakashi', bk)
    title = q.get('title', '')
    data = lookup(title, cache, bk or sources[0]['url'], full=True)
    sources = provider_season_sources(sources)
    episodes = variant_rows(sources, data)
    official = {part['season_number']: part for part in data.get('seasons', [])}
    art = q.get('art', '')
    from aniplay.metadata import get_image
    fan = get_image(data, 'backdrop_path', 'w1280')
    selected = q.get('season')
    params = {key: value for key, value in q.items() if key != 'action'}
    xbmcplugin.setPluginCategory(handle, title)
    if selected is None:
        history = History(profile)
        watched_urls = set().union(*(history.watched_for_show(src['url']) for src in sources))
        for number, rows in episodes.items():
            info = official.get(number, {})
            heading = season_title(number, info.get('name'), 'Outros episódios' if number < 0 else '')
            prefix, separator, arc = heading.partition(' · ')
            label = prefix + separator + (yellow(arc) if arc else '')
            watched = sum(any(option['url'] in watched_urls for option in options) for options in rows)
            item(f'{label} ({len(rows)})', 'multi_episodes', dict(params, season=number),
                 info, art, icon='season', fan=fan, info=dict(title=label, sorttitle=heading, mediatype='season',
                 tvshowtitle=title, season=max(0, number)), season_progress=(watched, len(rows)))
        return
    number = int(selected)
    ref = provider_reference(sources[0]['url'])
    show_id = (data.get('id') if data.get('media_type') == 'tv' else ref[1] if ref else None) if number >= 0 else None
    tmdb = season_details(show_id, number, cache) if show_id else {}
    details = {entry['episode_number']: entry for entry in tmdb.get('episodes', [])}
    cast = (tmdb.get('credits') or data.get('credits') or {}).get('cast')
    rows = episodes.get(number, [])
    offset = max(0, int(q.get('offset', '0')))
    for options in rows[offset:offset + 24]:
        episode = options[0]
        local = episode['local']
        meta = dict(details.get(int(local), {})) if local.isdigit() else {}
        suffix = re.search(r'\b(?:ep\.?|epis[oó]dio|episode)\s*[-:#]?\s*\d+(?:[.,]\d+)?\s*[-:·–]\s*(.+)$', episode['name'], re.I)
        heading = meta.get('name') or (suffix[1] if suffix else episode['name'] if not local or number < 0 else '')
        label = episode_title(local, heading)
        values = dict(url=episode['url'], provider=site, show_url=episode['parent'], show_title=title,
                      title=label, art=episode['art'] or art, episode_title=heading, season=number,
                      raw=episode['raw'], local=local)
        audio = audio_variants(options)
        if len(audio) > 1:
            values['audio_options'] = encode(audio)
        if show_id:
            values['showid'] = show_id
        if number < 0:
            values.pop('season', None)
        item(label, 'play', values, meta, values['art'], icon='episode', cast=cast, fan=fan)
    if len(rows) > offset + 24:
        item('Próxima página', 'multi_episodes', dict(params, offset=offset + 24), icon='next')


def select_external_audio():
    options = json.loads(q.get('audio_options', '[]'))
    if len(options) < 2:
        return True
    site = q['provider']
    for option in options:
        check_source(site, option['url'])
        check_source(site, option['parent'])
    choice = xbmcgui.Dialog().select('Como quer assistir?', [option['audio'] for option in options])
    if choice < 0:
        return False
    option = options[choice]
    q.update(url=option['url'], show_url=option['parent'], raw=option['raw'])
    return True


def select_bakashi_edition():
    from aniplay.catalog import groups, load_show
    from source import audio_sources
    sources = json.loads(q.get('audio_parents', '[]'))
    if len(sources) < 2 or not q.get('local', '').isdigit():
        return True
    number = int(q.get('season', '1'))
    matching = [src for src in sources if src['url'] == q.get('show_url') or src.get('season') in (None, number)]
    if not any(src.get('audio') for src in matching):
        return True
    options = {}
    for src in matching:
        check_source('Bakashi', src['url'])
        audio = src.get('audio', '')
        # The selected edition already supplied the episode URL.
        if src['url'] == q.get('show_url'):
            try:
                offered = [label for label in audio_sources(cache.get(q['url']), q['url'])
                           if label in ('Dublado', 'Legendado')]
            except (OSError, ValueError):
                offered = []
            for label in offered or [audio or 'Áudio do servidor']:
                options.setdefault(label, (q['url'], src['url'], label if offered else audio))
            continue
        if not audio or audio in options:
            continue
        try:
            body, _, show, _, _ = load_show(src['url'], full=False)
            for _, kind, season, rows in groups(body, show, src['url']):
                if kind != 'episodes' or (src.get('season') or season) != number:
                    continue
                found = [row for row, local in rows if str(local) == q['local']]
                if len(found) == 1:
                    options[audio] = (found[0]['url'], src['url'], audio)
                    break
        except (OSError, ValueError):
            continue
    if not options:
        return True
    labels = list(options)
    requested = q.get('preferred_audio')
    if requested in options:
        selected = requested
    elif requested:
        from aniplay.playback import choose_other_audio
        selected = choose_other_audio(requested, labels)
        if not selected:
            return False
    else:
        selection = xbmcgui.Dialog().select('Como quer assistir?', labels) if len(labels) > 1 else 0
        if selection < 0:
            return False
        selected = labels[selection]
    url, parent, audio = options[selected]
    check_source('Bakashi', url)
    q.update(url=url, show_url=parent, preferred_audio=audio)
    return True
