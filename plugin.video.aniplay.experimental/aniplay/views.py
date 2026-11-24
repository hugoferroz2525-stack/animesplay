from aniplay import videotag
import json
import os
import sys
import xbmcgui
import xbmcplugin
from source import recent_searches
from urllib.parse import urlencode
from aniplay.runtime import root, cache, handle, action, addon
from aniplay.titles import clean_text, highlight_episode_title
from functools import lru_cache
from aniplay.data_files import load
from aniplay.tmdb_match import catalog_title, slug

@lru_cache(maxsize=1)
def durations():
    return load("catalog-durations.json")

pending_progress = []

def yellow(s):
    return '[COLOR FFFFD32D]' + str(s) + '[/COLOR]'

def rated(name, data):
    if addon.getSettingBool('poster_badges'):
        return name
    return name + ('  ' + yellow('★ %.1f' % data['vote_average']) if data.get('vote_average') and (data.get('vote_count') or 'vote_count' not in data) else '')

listed = 0
pending_items = []

def flush():
    if pending_progress:
        from aniplay.storage.history import History
        from aniplay.runtime import profile
        progress = History(profile).progress_for(url for urls, _ in pending_progress for url in urls)
        for urls, li in pending_progress:
            states = [progress[url] for url in urls if url in progress]
            if states:
                watched = any(row[2] for row in states)
                position, duration, _, in_progress = next((row for row in states if row[3]), states[0])
                tag = li.getVideoInfoTag()
                tag.setPlaycount(int(watched))
                if in_progress:
                    tag.setResumePoint(position, duration)
        pending_progress.clear()
    if pending_items:
        xbmcplugin.addDirectoryItems(handle,pending_items,len(pending_items))
        pending_items.clear()


def configure_actions(li, route, params, details, data, label, thumb, fan):
    context = []
    if route in ('show', 'multi_servers') and params.get('url') and not params.get('server_entry'):
        command = 'unfavorite' if action == 'favorites' else 'favorite'
        args = dict(action=command,url=params['url'],title=details['title'],art=thumb)
        if params.get('sources'):
            args['sources'] = params['sources']
        address = sys.argv[0]+'?'+urlencode(args)
        caption = 'Remover da minha lista' if command=='unfavorite' else 'Salvar na minha lista'
        identify = sys.argv[0]+'?'+urlencode(dict(action='identify',url=params['url'],title=data.get('name') or (params or {}).get('episode_title') or (params or {}).get('title') or label))
        context.append((caption,'RunPlugin('+address+')'))
    def command_url(command, **values):
        return sys.argv[0]+'?'+urlencode(dict(action=command,**values))
    if route in ('show', 'multi_servers') and params.get('url') and not params.get('server_entry'):
        values=dict(url=params['url'],title=data.get('name') or (params or {}).get('episode_title') or (params or {}).get('title') or label,art=thumb,plot=details['plot'])
        for caption,command,method in [('Títulos semelhantes','similar','Container.Update'),('Elenco','cast','Container.Update'),('Trailer','trailer','RunPlugin'),('Exportar para a biblioteca do Kodi','export','RunPlugin')]:
            if command == 'export' and params.get('sources') and not any(row['site'] == 'Bakashi' for row in json.loads(params['sources'])):
                values = dict(values, sources=params['sources'])
            context.extend([(caption,method+'('+command_url(command,**values)+')')])
        context.append(('Identificar no TMDB','RunPlugin('+identify+')'))
    if route == 'query' and params:
        context.extend([('Editar esta busca','RunPlugin('+command_url('edit_term',term=params['term'])+')'),('Apagar esta busca','RunPlugin('+command_url('delete_term',term=params['term'])+')')])
    if route in ('play','episodes') and params and params.get('showid'):
        values={k:params[k] for k in ('showid','season','local') if params.get(k) != '' and k in params}
        if route=='episodes' or 'local' in values:
            context.extend([('Trailer','RunPlugin('+command_url('trailer',**values)+')')])
    if route == 'play':
        if params.get('movie_id'):
            values = dict(params, plot=details['plot'], fan=fan)
            context.append(('Informações do filme', 'RunPlugin('+command_url('episode_info', **values)+')'))
            context.append(('Trailer', 'RunPlugin('+command_url('trailer',movie_id=params['movie_id'])+')'))
        edit_url = sys.argv[0]+'?'+urlencode(dict(action='opening',url=params['url']))
        context.extend([('Ajustar abertura deste episódio','RunPlugin('+edit_url+')')])
        variants = json.loads(params.get('audio_options', '[]'))
        pending_progress.append(([params['url']] + [row['url'] for row in variants], li))
        li.setProperty('IsPlayable','true')
    if context:
        li.addContextMenuItems(context)


def item(label, route, params=None, data=None, art='', icon='play', info=None, cast=None, fan='', season_progress=None, server_badge='', season_partial=False):
    global listed
    label = clean_text(label)
    from aniplay.menu_metadata import resolve
    data = resolve(route,params,cache) if data is None else data
    params = params or {}
    fields = dict(info or {})
    title = data.get('name') or params.get('episode_title') or params.get('title') or label
    if route == 'show' and action != 'calendar_day':
        title = catalog_title(label, data, params.get('url', ''), addon.getSettingBool('original_titles'))
        label = title
    if route == 'play':
        fields = {**videotag.episode_fields(params), **fields}
    if route == 'show' and data.get('media_type') in ('tv', 'movie'):
        fields['mediatype'] = {'tv': 'tvshow', 'movie': 'movie'}[data['media_type']]
    if route in ('show','multi_servers') and not data.get('runtime') and not any(data.get('episode_run_time') or []):
        recent = (data.get('last_episode_to_air') or {}).get('runtime')
        seconds = recent * 60 if recent else durations().get(slug(params.get('url', '')))
        if seconds:
            fields.setdefault('duration', seconds)
    title = fields.pop('title', title)
    if route == 'play' and fields['mediatype'] == 'episode':
        fields.setdefault('sorttitle', label)
        label = highlight_episode_title(label, params.get('episode_title') or data.get('name'), yellow)
        title = label
    elif route == 'similar' or (route == 'show' and action == 'calendar_day'):
        # Alguns modos do Kodi exibem InfoTagVideo.Title no lugar do rótulo.
        title = label
    poster = ''
    rating_badge = addon.getSettingBool('poster_badges')
    if server_badge or (route in ('show', 'episodes', 'multi_servers') and data.get('poster_path') and rating_badge):
        from aniplay.metadata import get_image
        from aniplay.poster_badges import get_poster
        from aniplay.runtime import profile
        address = get_image(data, 'poster_path', 'w500') or art
        poster = get_poster(profile, address, data.get('vote_average') if rating_badge else None,
                            data.get('vote_count'), server_badge)
    if route in ('show', 'play', 'episodes', 'multi_servers') and not poster:
        label = rated(label, data)
    li = xbmcgui.ListItem(label=label, offscreen=True)
    if season_progress:
        watched, total = season_progress
        li.setProperty('WatchedEpisodes', str(watched))
        if season_partial:
            li.setProperty('AniPlay.SeasonProgress', f'{watched} vistos · lista parcial')
        else:
            li.setProperty('TotalEpisodes', str(total))
            li.setProperty('UnWatchedEpisodes', str(total - watched))
            li.setProperty('AniPlay.SeasonProgress', f'{watched} de {total} vistos')
            li.setProperty('AniPlay.SeasonPercent', str(round(100 * watched / total)) if total else '0')
    icon_path = os.path.join(root, 'resources', 'icons', icon + '.png')
    details, thumb, fan = videotag.decorate(li, data, title=title, fields=fields, art=art,
                                            fan=fan or data.get('site_fanart') or os.path.join(root, 'fanart.jpg'),
                                            icon=icon_path, cast_override=cast, poster_override=poster)
    action_art = get_image(data, 'poster_path', 'w500') if poster else thumb
    configure_actions(li,route,params,details,data,label,action_art,fan)
    path = sys.argv[0] + '?' + urlencode(dict(action=route, **(params or {})))
    pending_items.append((path,li,route not in ('play','prompt','person_prompt','settings','clear')))
    listed += 1

def search_menu():
    item('Nova busca','prompt',icon='search',info=dict(plot='Digite o título em português, japonês ou inglês.'))
    item('Buscar pessoa','person_prompt',icon='person',info=dict(plot='Buscar artistas e encontrar os animes disponíveis no Bakashi.'))
    terms = recent_searches(cache.user)
    for term in terms:
        item(term,'query',dict(term=term),icon='repeat',info=dict(plot='Repetir a busca por '+term+'.'))
    if terms:
        item('Limpar histórico','clear',icon='clear',info=dict(plot='Abrir a confirmação para apagar as pesquisas deste perfil.'))
