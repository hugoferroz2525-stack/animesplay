from aniplay import videotag
from aniplay.data_files import load as load_data
from aniplay.flix_ui import get_cast
import xbmcgui
from aniplay.metadata import tm, lookup, details, episode_details, get_image
from aniplay.runtime import cache, q, action
from aniplay.views import item
from aniplay.tmdb_match import index
from source import BASE


def display(data, title, poster='', fan='', people=None, fields=None):
    from aniplay.titles import clean_text
    li = xbmcgui.ListItem(label=clean_text(title))
    videotag.decorate(li, data, title=title, fields=fields, art=poster, fan=fan,
                     cast_override=people, include_artwork=True)
    xbmcgui.Dialog().info(li)


def show_details():
    d=lookup(q['title'],cache,q['url'],full=True)
    return d or {'name':q['title'],'overview':q.get('plot','')}


def episode_info():
    from aniplay.episode_context import restore
    try:
        snapshot = restore(q)
    except (OSError, ValueError, KeyError):
        snapshot = {}
    if str(q.get('movie_id', '')).isdigit():
        data = details('movie', q['movie_id'], cache, full=True)
    elif q.get('showid') and q.get('local', '').isdigit():
        data = episode_details(q['showid'], q['season'], q['local'], cache)
    else:
        data = {}
    base = snapshot.get('data', {})
    data = {**base, **{key: value for key, value in data.items() if value}}
    collection = data.get('belongs_to_collection') or {}
    if collection.get('id') and not collection.get('overview'):
        extra = details('collection', collection['id'], cache)
        if extra.get('overview'):
            data['belongs_to_collection'] = {**collection, 'overview': extra['overview']}
    data['overview'] = data.get('overview') or q.get('plot', '')
    title = data.get('name') or q.get('episode_title') or q.get('title', '')
    display(data, title, q.get('art', ''), q.get('fan') or snapshot.get('fan', ''),
            people=snapshot.get('cast'), fields=videotag.episode_fields(q))


def related(results):
    catalog=load_data('catalog-links.json')
    by_id={}
    for key,(kind,ident,_) in index().items():
        if key in catalog:
            by_id.setdefault((kind,ident),[]).append(catalog[key])
    from aniplay.catalog_updates import rows
    for _,name,url,art,kind,ident in rows():
        if ident:
            by_id.setdefault((kind,ident),[]).append((name,url,art))
    matches = {}
    for result in results:
        for name, url, art in by_id.get((result.get('media_type', 'tv'), result.get('id')), []):
            matches.setdefault(url, dict(name=name, url=url, art=art))
    entries = list(matches.values())
    if entries:
        from aniplay.catalog import catalog_metadata
        for entry, data in zip(entries, catalog_metadata(entries)):
            item(entry['name'], 'show', dict(url=entry['url']), data=data, art=entry['art'])


def directory():
    if action=='trending':
        results=[]
        for page in range(1,4):
            batch=tm('discover/tv',cache,with_genres='16',with_original_language='ja',
                     sort_by='popularity.desc',page=page).get('results',[])
            if not batch:
                break
            results.extend(batch)
        related(results)
        return
    if action=='people':
        for person in get_cast(tm('search/person', cache, query=q['term']).get('results') or []):
            if person['id']:
                item(person['name'], 'person', dict(id=person['id']), art=person['thumbnail'], icon='person')
        return
    if action=='person':
        credits=tm('person/'+q['id']+'/combined_credits',cache)
        related(credits.get('cast',[])+credits.get('crew',[]))
        return
    d=show_details()
    if action=='similar':
        if d.get('id') and d.get('media_type') in ('tv','movie'):
            path='%s/%s/similar'%(d['media_type'],d['id'])
            related([dict(r,media_type=d['media_type']) for r in tm(path,cache).get('results',[])])
        return
    if action=='cast':
        for person in get_cast((d.get('credits') or {}).get('cast') or []):
            label = ' · '.join(part for part in (person['name'], person['role']) if part)
            if person['id']:
                item(label, 'person', dict(id=person['id']), art=person['thumbnail'], icon='person',
                     info=dict(plot='Ver outros títulos deste artista no Bakashi.'))
        return
    display(d,d.get('name',q['title']),get_image(d,'poster_path','w500') or q.get('art',''),get_image(d,'backdrop_path','w1280'),(d.get('credits') or {}).get('cast'))
