"""Associa itens de navegação à obra do catálogo sem adivinhar episódios."""
import re
from functools import lru_cache
from aniplay.data_files import load as load_data
from urllib.parse import parse_qs, urlsplit
from aniplay.tmdb_match import normalized, slug
from aniplay.metadata import lookup, details, episode_details


@lru_cache(maxsize=1)
def catalog():
    records=load_data('catalog-links.json')
    from aniplay.catalog_updates import rows
    records.update({key:(name,url,art) for key,name,url,art,_,_ in rows()})
    names={}
    for record in records.values():
        title=normalized(record[0])
        names[title]=record if title not in names else None
    return records,names


def resolve(route,params,cache):
    if route not in ('show','play','catalog') or not params:
        return {}
    url=params.get('url','')
    if route == 'show':
        record = catalog()[0].get(slug(url))
        title = record[0] if record else params.get('title') or slug(url).replace('-', ' ')
        data = lookup(title, cache, url, full=True)
        if record:
            data.setdefault('site_poster', record[2])
        return data
    from aniplay.episode_context import cached
    if route == 'play':
        snapshot = cached(params)
        if snapshot:
            data = dict(snapshot['data'])
            data['site_fanart'] = snapshot.get('fan', '')
            credits = dict(data.get('credits') or {})
            if not credits.get('cast') and snapshot.get('cast'):
                credits['cast'] = snapshot['cast']
            data['credits'] = credits
            return data
        if str(params.get('movie_id', '')).isdigit():
            return details('movie', params['movie_id'], cache, full=True)
    records,names=catalog()
    key=slug(params.get('show_url') or url)
    if route=='play' and not params.get('show_url'):
        key=re.sub(r'-\d+-episodio-.*$', '',key)
    record=records.get(key)
    if route=='catalog':
        term=parse_qs(urlsplit(url).query).get('search',[''])[0]
        record=names.get(normalized(term))
    if route == 'play' and params.get('showid') and str(params.get('local','')).isdigit():
        episode = episode_details(params['showid'], params['season'], params['local'], cache)
        if episode.get('id'):
            if record:
                params.setdefault('show_title', record[0])
                episode['site_poster']=record[2]
            credits = episode.get('credits', {})
            episode['guest_stars'] = credits.get('guest_stars') or episode.get('guest_stars', [])
            return episode
    if not record:
        return {}
    title,url,poster=record
    data=dict(lookup(title,cache,url))
    data.setdefault('site_poster',poster)
    if route=='play':
        for field in ('id', 'name', 'vote_average', 'vote_count'):
            data.pop(field,None)
        if data.get('overview'):
            data['overview']='Sobre a série · '+data['overview']
    return data
