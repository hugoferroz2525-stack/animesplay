from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, urlsplit, urlunsplit
import xbmc
import xbmcgui
import xbmcplugin
from source import BASE, Cache, cards, episode_list, match
import re
from urllib.parse import urlencode, urljoin
from aniplay.runtime import addon, database, cache, handle, q, action, token
from aniplay.metadata import tm, lookup, details, reference, get_image, season_details, cloud_cards
from aniplay.tmdb_match import bakashi_metadata, catalog_title, editions, normalized, slug
from aniplay.episode_order import flat_season_position, flat_season_ranges, metadata_numbers
from aniplay.views import yellow, rated, item, search_menu
from aniplay.titles import episode_title, season_title

def catalog_metadata(entries):
    keys = []
    by_id = {}
    if addon.getSettingBool('cloud_cards'):
        for entry in entries:
            ref = reference(entry['url'], cache)
            keys.append(f'{ref[0]}/{ref[1]}' if ref and ref[0] in ('tv', 'movie') else None)
        ids = sorted(set(filter(None, keys)))
        for start in range(0, len(ids), 25):
            batch = ids[start:start + 25]
            by_id.update({key: data for key, data in cloud_cards(batch, cache).items()
                          if str(data['id']) == key.split('/')[1]
                          and data.get('media_type', key.split('/')[0]) == key.split('/')[0]})

    metadata = [by_id.get(key, {}) for key in keys] if keys else [{} for _ in entries]

    def find(index):
        entry = entries[index]
        db = Cache(database)
        try:
            return lookup(entry['name'], db, entry['url'], full=True)
        finally:
            db.user.close()
            db.db.close()

    missing = [i for i, data in enumerate(metadata) if not data]
    if token and missing:
        with ThreadPoolExecutor(max_workers=6) as pool:
            for i, data in zip(missing, pool.map(find, missing)):
                metadata[i] = data
    elif missing:
        fallback = bakashi_metadata()
        for i in missing:
            if urlsplit(entries[i]['url']).hostname == urlsplit(BASE).hostname:
                metadata[i] = dict(fallback.get(slug(entries[i]['url']), {}))
    return metadata


def catalog():
    url = q.get('url', BASE+'/lista-de-animes')
    if action == 'query':
        term = q.get('term','')
        if not term:
            search_menu()
            return
        url = BASE+'/lista-de-animes?'+urlencode({'search':term})
    try:
        if q.get('offline') == '1' and action == 'catalog':
            offline_catalog()
            return
        params = dict(parse_qsl(urlsplit(url).query))
        if action == 'catalog' and params.get('type') in FORMATS:
            format_catalog(params['type'], url, params)
            return
        body = '' if ',' in params.get('genre', '') else cache.get(url)
    except (OSError, ValueError):
        if action != 'catalog' or url != BASE + '/lista-de-animes':
            raise
        offline_catalog()
        return
    entries = cards(body)
    if action == 'query' and token and not entries:
        from aniplay.info import related
        from aniplay.metadata import search
        related(search(term, cache))
        return
    if ',' in params.get('genre', ''):
        entries, more = grouped_genre(params)
        body = 'rel="next"' if more else ''
    metadata = catalog_metadata(entries)
    from aniplay.catalog_updates import record
    record(entries,metadata)
    from aniplay.multisite import grouped, show_groups
    groups = grouped([('Bakashi', e['name'], e['url'], e['art']) for e in entries])
    show_groups(groups, {e['url']: {'overview': e['plot']} for e in entries},
                {e['url']: d for e, d in zip(entries, metadata)})
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    page = int(query.get('page',1))
    if any(int(n)>page for n in re.findall(r'data-page="(\d+)"', body)) or re.search(r'rel="next"', body):
        query['page'] = page+1
        params=dict(url=urlunsplit(parts._replace(query=urlencode(query))))
        if addon.getSettingBool('keep_view'):
            params['view']=xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId()
        item('Próxima página','catalog',params,icon='next')

def grouped_genre(params):
    page = max(1, int(params.get('page', 1)))
    seen = set()
    active = list(dict.fromkeys(params['genre'].split(',')))
    rows = []
    for number in range(1, page + 1):
        rows = []
        following = []
        for genre in active:
            query = dict(genre=genre)
            if number > 1:
                query['page'] = number
            body = cache.get(BASE + '/lista-de-animes?' + urlencode(query))
            for entry in cards(body):
                if entry['url'] not in seen:
                    seen.add(entry['url'])
                    rows.append(entry)
            if any(int(n) > number for n in re.findall(r'data-page="(\d+)"', body)) or 'rel="next"' in body:
                following.append(genre)
        active = following
    return rows, bool(active)


FORMATS = {'tv': 'TV Anime', 'movie': 'Filme', 'ova': 'OVA', 'ona': 'ONA', 'special': 'Especial'}


def format_catalog(format_id, url, params):
    from aniplay.data_files import load

    formats = load('catalog-formats.json')
    catalog = load('catalog-links.json')
    page = max(1, int(params.get('page', '1')))
    from aniplay.multisite import grouped, representative, show_groups
    groups = grouped([('Bakashi', *catalog[key]) for key, value in formats.items()
                      if value == FORMATS[format_id] and key in catalog])
    start = (page - 1) * 25
    selected = groups[start:start + 25]
    saved = {}
    for group in selected:
        url = representative(group)['url']
        ref = reference(url, cache)
        data = details(ref[0], ref[1], cache, full=True, cached_only=True) if ref else {}
        saved[url] = data or bakashi_metadata().get(slug(url), {})
    show_groups(selected, metadata=saved)
    if start + 25 < len(groups):
        params['page'] = page + 1
        next_url = urlunsplit(urlsplit(url)._replace(query=urlencode(params)))
        item('Próxima página', 'catalog', dict(url=next_url), icon='next')


def offline_catalog():
    from aniplay.data_files import load
    from aniplay.flix_ui import notification

    page = max(1, int(q.get('page', '1'))) if q.get('page', '1').isdigit() else 1
    from aniplay.multisite import grouped, representative, show_groups
    records = sorted(load('catalog-links.json').values(), key=lambda record: normalized(record[0]))
    groups = grouped([('Bakashi', *record) for record in records])
    start = (page - 1) * 25
    if page == 1:
        notification('Exibindo o índice local do catálogo.', 'Catálogo salvo', 'offline')
    selected = groups[start:start + 25]
    data = {src['url']: bakashi_metadata().get(slug(src['url']), {})
            for src in (representative(group) for group in selected)}
    show_groups(selected, metadata=data)
    if start + 25 < len(groups):
        item('Próxima página', 'catalog', dict(offline=1, page=page + 1), icon='next')
    if page > 1:
        item('Página anterior', 'catalog', dict(offline=1, page=page - 1), icon='next')


def load_show(url, *, full=True, db=cache):
    body = db.get(url)
    name = match(r'<h1[^>]*>(.*?)</h1>',body)
    year = match(r'</h1>.*?\b((?:19|20)\d{2})\s*<span',body)
    show = lookup(name,db,url,full=full,year=year)
    if not show.get('overview'):
        site_plot = match(r'class="entry[^"]*"[^>]*>\s*<p>(.*?)</p>',body)
        if site_plot:
            show['overview'] = re.sub(r'<[^>]+>', '',site_plot)
    poster = match(r'<img\s+src="([^"]+)"\s+alt="[^"]*Poster',body)
    fan = match(r'src="([^"]+)"\s+alt="[^"]*Backdrop',body)
    return body,name,show,poster,fan

def groups(body,show,url, *, section=None, counts=False, preferred_season=None, parallel=False, db=cache):
    explicit = re.findall(r'<a href="([^"]+)"[^>]*>\s*<span>Temporada (\d+)</span>',body)
    current = int(match(r"season:\s*'(\d+)'",body,'1'))
    links = explicit or [(url,str(current))]
    if preferred_season:
        links = sorted(links, key=lambda pair: pair[1] != preferred_season)
    mapping = reference(url,db)
    dedicated = mapping and (mapping[2] not in (None,1) or slug(url) in editions())
    links = [(urljoin(BASE, link), number) for link, number in links]
    links = [(link, number) for link, number in links if not section or link == section]
    if parallel and len(links) > 1:
        def load(pair):
            db = Cache(database)
            try:
                rows = list(section_groups(db, pair, url, body, show, current, explicit, dedicated, counts))
                return rows, db.stale
            finally:
                db.user.close()
                db.db.close()

        with ThreadPoolExecutor(max_workers=5) as pool:
            for rows, stale in pool.map(load, links):
                cache.stale |= stale
                yield from rows
    else:
        for pair in links:
            yield from section_groups(db, pair, url, body, show, current, explicit, dedicated, counts)


def section_groups(db, pair, url, body, show, current, explicit, dedicated, counts):
    link, s = pair
    page = body if link == url else db.get(link)
    for kind in ('episodes','specials','movies'):
        if kind != 'episodes' and 'data-target="'+kind+'-container"' not in page:
            continue
        seasons = sorted((x for x in (show.get('seasons') or []) if x['season_number']>0), key=lambda x:x['season_number'])
        flat = not dedicated and not explicit and current == 1 and kind == 'episodes' and len(seasons)>1
        if counts and not flat:
            count = episode_list(db,page,kind,count_only=True)
            if count:
                yield link,kind,int(s),range(count)
            continue
        entries = episode_list(db,page,kind)
        numbers = [int(e['num']) if e['num'].isdigit() else None for e in entries]
        ranges = flat_season_ranges(seasons, numbers) if flat else []
        buckets = {}
        for entry, number in zip(entries, numbers):
            season, local = flat_season_position(ranges, number) if ranges else (int(s), number)
            buckets.setdefault(season, []).append((entry, local))
        for season,rows in buckets.items():
            yield link,kind,season,rows

def season_summary(summary, show, number, heading, count, is_series):
    summary = dict(summary)
    if summary.get('id') and not summary.get('overview') and is_series:
        english = tm('tv/%s/season/%s' % (show['id'],number),cache,language='en-US',cached_only=True)
        if english.get('id')==summary['id'] and english.get('overview'):
            summary['overview'] = english['overview']
    if not summary.get('overview'):
        summary['overview'] = '%s · %d episódio(s) no Bakashi.' % (heading,count)
        if show.get('overview'):
            summary['overview'] += '\n\nSobre a série: '+show['overview']
    return summary

def episode_item_data(e, d, name, show, number, local, movie, collection, fan, poster, show_url):
    site_thumb = e['art'] if 'placeholder' not in e['art'].lower() else ''
    thumb = get_image(d,'still_path','w780') or site_thumb
    thumb = thumb or fan or poster
    title = d.get('name') or e['name']
    identified_movie = movie and d.get('id')
    label = title if identified_movie else episode_title(e['num'], title)
    params = dict(url=e['url'], title=title if identified_movie else episode_title(e['num'], title, name),
                  art=thumb, showid=show.get('id','') if not movie and not collection else '',
                  season=number, local=local if local is not None else '', raw=e['num'],
                  show_url=show_url, show_title=name, episode_title=title)
    if q.get('preferred_audio'):
        params['preferred_audio'] = q['preferred_audio']
    if q.get('audio_parents'):
        params['audio_parents'] = q['audio_parents']
    if identified_movie:
        params['movie_id'] = d['id']
    return label, params, thumb


def series(show_url=None, *, target=None, preferred_season=None, db=cache, server_sources=None, seen_seasons=None, season_hint=None):
    show_url = show_url or q['url']
    associations = []
    remaining = False
    exported = 0
    body,name,show,poster,fan = load_show(show_url, full=not target, db=db)
    name = catalog_title(name, show, show_url, addon.getSettingBool('original_titles'))
    if not target and server_sources is None:
        xbmcplugin.setPluginCategory(handle,rated(name,show))
    mapping = reference(show_url,db)
    movie = show.get('media_type') == 'movie'
    collection = show.get('media_type') == 'collection'
    edition = editions().get(slug(show_url),{})
    use_order = bool(edition) and edition['id'] == show.get('id')
    cast = (show.get('credits') or {}).get('cast') or []
    section = q['section'] if not target and action == 'episodes' else None
    counts = not target and (action == 'show' or server_sources is not None)
    watched_urls = set()
    if counts and not movie and not collection:
        from aniplay.runtime import profile
        from aniplay.storage.history import History
        watched_urls = History(profile).watched_for_show(show_url)
    for link,kind,s,rows in groups(body,show,show_url,section=section,counts=counts and not watched_urls,
                                   preferred_season=preferred_season, parallel=counts, db=db):
        if target and not any(entry['url'] == target for entry, _ in rows):
            continue
        number = 0 if kind=='specials' else s
        if kind == 'episodes' and mapping and mapping[2] is not None and s == 1 and not re.search(r'<span>Temporada \d+</span>',body):
            number = mapping[2]
        applied_hint = (season_hint if kind == 'episodes' and s == 1
                        and not re.search(r'<span>Temporada \d+</span>', body) else None)
        if applied_hint:
            number = applied_hint
        if counts and seen_seasons is not None:
            key = (number, kind)
            if key in seen_seasons:
                continue
            seen_seasons.add(key)
        if section and q.get('season_hint'):
            number = int(q['season_hint'])
        summary = dict(next((p for p in (show.get('seasons') or []) if p['season_number']==number),{}))
        heading = ('Especiais' if number == 0 else
                   {'movies': 'Filmes'}.get(kind, 'Temporada '+str(s) if s>=0 else 'Outros episódios'))
        if collection:
            heading,summary = 'Coleção',dict(show)
        if movie:
            heading = 'Filme'
            summary = dict(show)
        if section and (s != int(q['s']) or kind != q['kind']):
            continue
        is_series = bool(show.get('id') and not collection and not movie and number>=0 and kind!='movies')
        season = season_details(show['id'],number,db,cached_only=counts,translate=not counts) if is_series else {}
        season_cast = (season.get('credits') or {}).get('cast') or cast
        if counts:
            summary.update({key: value for key, value in season.items() if key != 'episodes' and value})
            summary = season_summary(summary,show,number,heading,len(rows),is_series)
            media_type = 'movie' if movie else 'season'
            heading = season_title(number, summary.get('name'), heading)
            prefix, separator, arc = heading.partition(' · ')
            display = f'{prefix}{separator}{yellow(arc)}' if separator else heading
            title = f'{display} ({len(rows)})'
            progress = None
            if not movie and not collection and kind != 'movies':
                total = len(rows)
                watched = sum(entry['url'] in watched_urls for entry, _ in rows) if watched_urls else 0
                progress = (watched, total)
            item(title,'episodes',
                 dict(url=show_url,section=link,kind=kind,s=s,id=show.get('id',''),season=number,
                      showid=show['id'] if is_series else '', preferred_audio=q.get('preferred_audio', ''),
                      audio_parents=server_sources or '', season_hint=applied_hint or ''),summary,poster,icon='season',
                 info=dict(title=title,sorttitle=heading,tvshowtitle=name,season=number,
                           mediatype=media_type),cast=season_cast,fan=fan,season_progress=progress)
            continue
        eps = {x['episode_number']:x for x in season.get('episodes',[])}
        offset = sum(x.get('episode_count',0) for x in (show.get('seasons') or [])
                     if 0 < x['season_number'] < number)
        numbers = metadata_numbers(rows,eps,offset,edition['episodes'] if use_order else None)
        episode_rows = list(zip(rows, numbers))
        if section:
            page_offset = max(0, int(q.get('offset', '0')))
            remaining = len(episode_rows) > page_offset + 24
            episode_rows = episode_rows[page_offset:page_offset + 24]
        for (e,_),local in episode_rows:
            if target and e['url'] != target:
                continue
            d = dict(show if movie and len(rows)==1 else eps.get(local,{}))
            if is_series:
                for field in ('genres', 'production_companies', 'origin_country', 'content_ratings'):
                    if show.get(field) is not None:
                        d.setdefault(field, show[field])
            if not d.get('overview'):
                d['overview'] = e.get('plot') or ('%s · %s · Episódio %s.' % (name,heading,e['num']))
            label,params,thumb=episode_item_data(e,d,name,show,number,local,movie,collection,fan,poster,show_url)
            if target:
                return params, d, season_cast, fan
            associations.append((params, d, season_cast, fan))
            if action=='export':
                from aniplay.export import write_episode
                with cache.user:
                    cache.user.execute('BEGIN IMMEDIATE')
                    write_episode(name,params,number if number>=0 else s,str(local if local is not None else e['num']))
                exported += 1
                continue
            item(label,'play',params,d,thumb,icon='episode',cast=season_cast,fan=fan)
    if target:
        return {}
    if section and remaining:
        params = {key: value for key, value in q.items() if key != 'action'}
        params['offset'] = page_offset + 24
        item('Próxima página', 'episodes', params, icon='next')
    from aniplay.episode_context import remember
    with cache.db:
        for association in associations:
            remember(*association)
    if action=='show' and show.get('media_type') in ('tv','movie'):
        item('Títulos semelhantes','similar',dict(url=q['url'],title=name),icon='similar',
             info=dict(plot='Ver outras obras semelhantes disponíveis no Bakashi.'))
    return exported
