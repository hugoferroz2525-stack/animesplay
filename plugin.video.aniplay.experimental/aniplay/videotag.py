"""Metadados de vídeo do Kodi Nexus e posteriores."""
import xbmc
from aniplay.titles import clean_text

SETTERS = {
    'title': 'setTitle', 'plot': 'setPlot', 'originaltitle': 'setOriginalTitle',
    'premiered': 'setPremiered', 'duration': 'setDuration', 'genre': 'setGenres',
    'studio': 'setStudios', 'country': 'setCountries', 'mpaa': 'setMpaa',
    'year': 'setYear', 'mediatype': 'setMediaType', 'tvshowtitle': 'setTvShowTitle',
    'season': 'setSeason', 'episode': 'setEpisode', 'director': 'setDirectors',
    'writer': 'setWriters', 'tagline': 'setTagLine', 'aired': 'setFirstAired',
    'sorttitle': 'setSortTitle', 'sortseason': 'setSortSeason', 'sortepisode': 'setSortEpisode',
    'trailer': 'setTrailer', 'tags': 'setTags', 'setname': 'setSet', 'setoverview': 'setSetOverview',
}


def apply(item, details):
    tag = item.getVideoInfoTag()
    details = {key: clean_text(value) if isinstance(value, str) else value
               for key, value in details.items()}
    if details.get('status'):
        item.setProperty('AniPlay.Status', details['status'])
        if details.get('mediatype') == 'tvshow':
            tag.setTvShowStatus(details['status'])
    year = (details.get('premiered') or '')[:4]
    if year.isdigit() and not details.get('year'):
        details['year'] = int(year)
    for name, setter in SETTERS.items():
        value = details.get(name)
        if value is not None and value != '' and value != []:
            getattr(tag, setter)(value)
    if details.get('votes') or details.get('rating'):
        tag.setRating(float(details.get('rating') or 0), int(details.get('votes') or 0), 'tmdb', True)


def cast(item, people):
    actors = [xbmc.Actor(p['name'], p.get('role', ''), order, p.get('thumbnail', ''))
              for order, p in enumerate(people)]
    item.getVideoInfoTag().setCast(actors)


def tmdb_fields(data):
    from aniplay.flix_ui import directors, writers
    crew = (data.get('credits') or {}).get('crew') or data.get('crew') or []
    return dict(tagline=data.get('tagline'), status=data.get('status'),
                aired=data.get('air_date') if 'episode_number' in data else None,
                director=directors(crew), writer=writers(crew))


def production_code(item, data):
    if data.get('production_code'):
        item.getVideoInfoTag().setProductionCode(str(data['production_code']))
        item.setProperty('AniPlay.ProductionCode', str(data['production_code']))

def certification(data):
    for row in (data.get('content_ratings') or {}).get('results', []):
        if row.get('iso_3166_1') == 'BR' and row.get('rating'):
            return row['rating']
    for row in (data.get('release_dates') or {}).get('results', []):
        if row.get('iso_3166_1') == 'BR':
            return next((r['certification'] for r in row.get('release_dates', [])
                         if r.get('certification')), '')
    return ''


def episode_fields(params):
    if params.get('movie_id'):
        return {'mediatype': 'movie'}
    fields = {'mediatype': 'episode', 'tvshowtitle': params.get('show_title', '')}
    for name, value in (('season', params.get('season')),
                        ('episode', params['local'] if str(params.get('local')).isdigit() else params.get('raw'))):
        if str(value).isdigit():
            fields[name] = int(value)
    for name, key in (('sortseason', 'season'), ('sortepisode', 'episode')):
        if key in fields:
            fields[name] = fields[key]
    return fields


def decorate(item, data, *, title, fields=None, art='', fan='', icon='', cast_override=None, include_artwork=False, poster_override=''):
    """Use the same Kodi tags and artwork in lists, dialogs and playback."""
    import json
    from aniplay.metadata import get_image, trailer_url

    runtime = data.get('runtime') or next(iter(data.get('episode_run_time') or []), 0)
    collection = data.get('belongs_to_collection') or {}
    details = dict(title=title, sorttitle=title, plot=data.get('overview') or '',
                   originaltitle=data.get('original_name') or data.get('original_title'),
                   premiered=data.get('air_date') or data.get('first_air_date') or data.get('release_date'),
                   rating=data.get('vote_average'), votes=data.get('vote_count'),
                   duration=runtime * 60 if runtime else None,
                   genre=[entry['name'] for entry in (data.get('genres') or [])],
                   studio=[entry['name'] for entry in (data.get('production_companies') or [])],
                   country=data.get('origin_country') or [entry['iso_3166_1']
                                                         for entry in (data.get('production_countries') or [])],
                   mpaa=certification(data), trailer=trailer_url((data.get('videos') or {}).get('results', [])),
                   setname=collection.get('name'), setoverview=collection.get('overview'),
                   mediatype={'tv': 'tvshow', 'movie': 'movie'}.get(data.get('media_type')))
    keywords = data.get('keywords') or {}
    details['tags'] = [entry['name'] for entry in keywords.get('keywords', keywords.get('results', []))]
    if data.get('year'):
        details['year'] = int(data['year'])
    details.update(tmdb_fields(data))
    details.update(fields or {})
    apply(item, details)
    production_code(item, data)

    tag = item.getVideoInfoTag()
    ids = {'tmdb': str(data['id'])} if data.get('id') else {}
    external = data.get('external_ids') or {}
    for key in ('imdb', 'tvdb', 'wikidata'):
        value = external.get(key + '_id') or data.get(key + '_id')
        if value:
            ids[key] = str(value)
    if ids:
        tag.setUniqueIDs(ids, next(iter(ids)))

    aliases = data.get('alternative_titles') or {}
    titles = list(dict.fromkeys(entry['title'] for entry in aliases.get('titles', aliases.get('results', []))
                                if entry.get('title') and entry['title'] != title))
    if titles:
        item.setProperty('AniPlay.AlternativeTitles', json.dumps(titles, ensure_ascii=False))
    if details.get('mediatype') == 'tvshow':
        for season in (data.get('seasons') or []):
            if season.get('name') and season.get('season_number') is not None:
                tag.addSeason(season['season_number'], season['name'])

    images = data.get('images') or {}
    poster = poster_override or get_image(data, 'poster_path', 'w500') or art or data.get('site_poster', '')
    still = get_image(data, 'still_path', 'w780')
    thumb = still or poster
    if details.get('mediatype') == 'episode':
        thumb = still or art or poster
        poster = thumb
        icon = thumb or icon
    fanart = get_image(data, 'backdrop_path', 'w1280') or fan or data.get('site_fanart', '')
    artwork = dict(icon=icon, thumb=thumb or icon, poster=poster, fanart=fanart)
    if images.get('logos'):
        artwork['clearlogo'] = get_image(images['logos'][0], 'file_path', 'w500')
    item.setArt({key: value for key, value in artwork.items() if value})
    if include_artwork:
        for source, aspect, size in (('posters', 'poster', 'w500'), ('backdrops', 'fanart', 'w1280'),
                                     ('stills', 'thumb', 'w780'), ('logos', 'clearlogo', 'w500')):
            for image in images.get(source, []):
                url = get_image(image, 'file_path', size)
                if url:
                    tag.addAvailableArtwork(url, aspect)

    credits = data.get('credits') or {}
    credited = (credits.get('cast') or cast_override or []) + (credits.get('guest_stars') or data.get('guest_stars') or [])
    if credited:
        from aniplay.flix_ui import get_cast
        cast(item, get_cast(credited))
    return details, thumb, fanart
