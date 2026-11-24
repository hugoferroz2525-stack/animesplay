import json
import re
from urllib.parse import urlencode
from aniplay.runtime import addon, token, image_base
from aniplay.network import CATALOG_HOST, CLOUD_HOST, TMDB_HOST
from urllib.parse import urlsplit
from aniplay.providers.editions import reference as provider_reference
from aniplay.tmdb_match import bakashi_metadata, index, slug, unique_hit, title_variants, dated_hit

def tm(path, db, *, cached_only=False, **params):
    if not token:
        return {}
    headers = {}
    if re.fullmatch(r'[0-9a-fA-F]{32}',token):
        params['api_key'] = token
    else:
        headers['Authorization'] = 'Bearer ' + token
    url = 'https://api.themoviedb.org/3/' + path + '?' + urlencode({'language':addon.getSetting('tmdb_language') or 'pt-BR', **params})
    try:
        result = json.loads(db.get(url, headers, 86400 * (addon.getSettingInt('tmdb_days') or 7),
                                   json.loads, host=TMDB_HOST, cached_only=cached_only))
        return result if isinstance(result, dict) else {}
    except (ValueError, OSError):
        return {}

def cloud_cards(keys, db, *, language=None, cached_only=False):
    if not addon.getSettingBool('cloud_cards') or not keys:
        return {}
    lang = language or addon.getSetting('tmdb_language') or 'pt-BR'
    url = 'https://' + CLOUD_HOST + '/v3/cards?' + urlencode(dict(ids=','.join(sorted(set(keys))), lang=lang))
    try:
        result = json.loads(db.get(url, ttl=1800, validate=json.loads, host=CLOUD_HOST,
                                   cached_only=cached_only))
        cards = result.get('cards', {})
        return {key: card for key, card in cards.items() if key in keys and isinstance(card, dict) and card.get('id')}
    except (ValueError, OSError, AttributeError):
        return {}


def get_image(data, key, size="original"):
    """Adaptado de Flix/lib/tmdb.py."""
    path = data.get(key)
    return image_base + size + path if path else ''


def reference(url, db):
    db.user.execute('CREATE TABLE IF NOT EXISTS tmdb_choice (slug TEXT PRIMARY KEY, kind TEXT, id INTEGER)')
    choice = db.user.execute('SELECT kind,id FROM tmdb_choice WHERE slug=?',(slug(url),)).fetchone()
    if choice:
        return (*choice, None)
    if urlsplit(url).hostname == CATALOG_HOST:
        return index().get(slug(url))
    return provider_reference(url)


def search(name, db):
    return [h for h in tm('search/multi',db,query=name).get('results',[])
            if h.get('media_type') in ('movie','tv')]


def details(kind, ident, db, full=False, *, cached_only=False):
    params = {}
    if full and kind != 'collection':
        params = dict(append_to_response='credits,images,external_ids,alternative_titles,videos,keywords,content_ratings' if kind=='tv'
                      else 'credits,images,external_ids,alternative_titles,videos,keywords,release_dates',include_image_language='pt,en,null')
    data = tm('%s/%s' % (kind,ident),db,cached_only=cached_only,**params)
    if not data and kind in ('tv', 'movie'):
        key = f'{kind}/{ident}'
        card = cloud_cards([key], db, cached_only=cached_only).get(key, {})
        if str(card.get('id')) == str(ident):
            return card
    if data:
        data['media_type'] = kind
        if kind == 'movie':
            data.update(name=data.get('title'),original_name=data.get('original_title'),
                        first_air_date=data.get('release_date'))
    return data


def lookup(name, db, url, full=False, year=None):
    ref = reference(url,db)
    if ref:
        return details(ref[0],ref[1],db,full)
    fallback = bakashi_metadata().get(slug(url))
    if fallback:
        return dict(fallback)
    titles = title_variants(name)
    hits = {}
    for title in titles:
        for hit in search(title,db):
            hits[hit['media_type'],hit['id']] = hit
    results = list(hits.values())
    match = dated_hit(titles,results,year) if year else {}
    if not match:
        candidates = {}
        for title in titles:
            hit = unique_hit(title,results)
            if hit:
                candidates[hit['media_type'],hit['id']] = hit
        match = next(iter(candidates.values())) if len(candidates)==1 else {}
    return details(match['media_type'],match['id'],db,full) if match else {}


def trailer_url(videos):
    key = next((v['key'] for v in videos if v.get('site') == 'YouTube'
                and v.get('type') == 'Trailer' and v.get('key')), None)
    return 'plugin://plugin.video.youtube/play/?' + urlencode({'video_id': key}) if key else ''


def generic_title(value):
    return not value or bool(re.fullmatch(r'(?:episódio|episode)\s+\d+', value.strip(), re.I))


def needs_episode_translation(data):
    return any(not data.get(key) for key in ('overview', 'still_path')) or generic_title(data.get('name'))


def merge_episode_translation(data, fallback):
    for key in ('name', 'overview', 'still_path'):
        replace = not data.get(key) or (key == 'name' and generic_title(data.get('name'))
                                        and not generic_title(fallback.get('name')))
        if replace and fallback.get(key):
            data[key] = fallback[key]
    return data


def episode_details(show_id, season, episode, db):
    route = f'tv/{show_id}/season/{season}/episode/{episode}'
    data = tm(route, db, append_to_response='credits,images,external_ids,videos')
    if data.get('id') and needs_episode_translation(data):
        merge_episode_translation(data, tm(route, db, language='en-US'))
    return data


def season_details(ident, number, db, *, cached_only=False, translate=True):
    route = 'tv/%s/season/%s' % (ident,number)
    season = tm(route,db,append_to_response='credits',cached_only=cached_only)
    if not season:
        season = cloud_cards([route], db, cached_only=cached_only).get(route, {})
    episodes = season.get('episodes',[])
    if translate and any(needs_episode_translation(episode) for episode in episodes):
        english = tm(route,db,language='en-US',cached_only=cached_only)
        if not english:
            english = cloud_cards([route], db, language='en-US', cached_only=cached_only).get(route, {})
        translated = {episode['id']: episode for episode in english.get('episodes', [])}
        for episode in episodes:
            merge_episode_translation(episode, translated.get(episode['id'], {}))
    return season
