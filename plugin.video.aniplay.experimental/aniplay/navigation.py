from aniplay.flix_ui import notification
from aniplay.menus import HOME, DAYS, schedule
import library
import xbmc
import xbmcgui
import xbmcplugin
from source import filter_options
from source import BASE, cards
import json
from urllib.parse import urlencode
from aniplay.storage.history import History
from aniplay.runtime import profile
from aniplay.metadata import search, reference
from aniplay.tmdb_match import slug
from aniplay import views
from aniplay.runtime import addon, cache, handle, q, action
from aniplay.views import item, search_menu
from aniplay.catalog import catalog, series
from aniplay.playback import play

def home():
    for label,route,icon,description in HOME:
        item(label,route,icon=icon,info=dict(plot=description))


def recovery(message):
    item(message+' · Buscar anime','search',icon='empty')
    if action not in ('query','settings'):
        item('Tentar novamente',action,{k:v for k,v in q.items() if k!='action'},icon='retry')
    item('Menu principal','home',icon='home')

def run():
    if action=="index_update":
        from aniplay.catalog_updates import refresh
        refresh()
        return
    library.initialize(cache.user)
    if action in ACTIONS:
        ACTIONS[action]()
        return
    xbmcplugin.setContent(handle,{'catalog':'tvshows','query':'tvshows','search':'tvshows','show':'seasons','episodes':'episodes','latest':'episodes','multi_catalog':'tvshows','multi_seasons':'seasons','multi_episodes':'episodes'}.get(action,'videos'))
    if action in ('catalog', 'query', 'show', 'episodes', 'multi_seasons', 'multi_episodes'):
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_NONE)
        sort_method = xbmcplugin.SORT_METHOD_EPISODE if action in ('episodes', 'multi_episodes') else xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE
        xbmcplugin.addSortMethod(handle, sort_method)
    if action in SCREENS:
        SCREENS[action]()

    if not views.listed:
        from aniplay.runtime import token
        if not token and action in ('trending','people','person','cast','similar'):
            item('Configurar a chave do TMDB','settings',icon='settings',info=dict(plot='Esta consulta precisa de uma chave do TMDB.'))
        else:
            recovery('Nenhum resultado disponível')
    if cache.stale:
        notification('Exibindo a última página disponível.','Catálogo salvo','offline')
    views.flush()
    xbmcplugin.endOfDirectory(handle,cacheToDisc=False)
    view = q.get('view','')
    if addon.getSettingBool('keep_view') and view.isdigit() and 50 <= int(view) <= 599:
        xbmc.executebuiltin('Container.SetViewMode('+view+')')


def handle_anime_info():
    from aniplay import info
    if action == 'episode_info':
        info.episode_info()
    elif action == 'anime_info':
        info.directory()
    else:
        from aniplay.metadata import tm, trailer_url
        if q.get('movie_id'):
            path = 'movie/' + q['movie_id']
        elif q.get('showid'):
            path = 'tv/%s/season/%s' % (q['showid'], q['season'])
            if q.get('local'):
                path += '/episode/' + q['local']
        else:
            data = info.show_details()
            path = '%s/%s' % (data.get('media_type'), data.get('id')) if data.get('id') else ''
        videos = []
        if path:
            for language in dict.fromkeys((addon.getSetting('tmdb_language') or 'pt-BR', 'en-US', 'ja-JP')):
                videos.extend(tm(path + '/videos', cache, language=language).get('results', []))
        clip = trailer_url(videos)
        if clip and xbmc.getCondVisibility('System.HasAddon(plugin.video.youtube)'):
            xbmc.executebuiltin('PlayMedia(' + clip + ')')
        else:
            notification('Trailer ou complemento YouTube indisponível.')
    return


def handle_export():
    try:
        if q.get('sources'):
            from aniplay.multisite import export_provider
            count = export_provider()
        else:
            count = series()
    except (OSError, ValueError):
        notification('A exportação foi interrompida. Confira a pasta e tente novamente.', icon='alert')
    else:
        notification('%d arquivo(s) exportado(s). Adicione a pasta como fonte de vídeos no Kodi.' % count)
    return


def handle_purge():
    table = {'tmdb': 'tmdb_pages', 'pages': 'pages'}.get(q.get('scope'))
    if table and xbmcgui.Dialog().yesno('Cache', 'Apagar os dados salvos desta categoria?'):
        with cache.db:
            cache.db.execute(f'DELETE FROM {table}')
            if table == 'tmdb_pages':
                cache.db.execute('DROP TABLE IF EXISTS episode_links')
        notification('Cache limpo.')
    return


def handle_prompt():
    from source import recent_searches
    term = xbmcgui.Dialog().input('Buscar pessoa' if action == 'person_prompt' else 'Buscar anime', defaultt=q.get('term', '')).strip()
    if term:
        if action != 'person_prompt':
            if action == 'edit_term':
                with cache.user:
                    cache.user.execute('DELETE FROM searches WHERE term=?', (q['term'],))
            recent_searches(cache.user, term)
        route = 'people' if action == 'person_prompt' else q.get('search_route', 'query')
        if route not in ('people', 'query', 'multi_catalog'):
            route = 'query'
        xbmc.executebuiltin('Container.Update(plugin://plugin.video.aniplay.experimental/?' + urlencode(dict(action=route, term=term)) + ')')
    return


def handle_clear():
    with cache.user:
        if action == 'delete_term':
            cache.user.execute('DELETE FROM searches WHERE term=?', (q['term'],))
        elif xbmcgui.Dialog().yesno('Histórico', 'Apagar todas as buscas deste perfil?'):
            cache.user.execute('DELETE FROM searches')
    xbmc.executebuiltin('Container.Refresh')
    return


def handle_settings():
    addon.openSettings()
    return


def handle_opening():
    from aniplay.opening import configure
    configure(cache.user, q['url'])
    return


def handle_identify():
    term = xbmcgui.Dialog().input('Título para procurar no TMDB', defaultt=q['title']).strip()
    if not term:
        return
    hits = search(term, cache)
    if not hits:
        notification('Confira o título e a chave do TMDB.', 'Nenhuma correspondência', 'search')
        return
    labels = ['%s · %s · %s' % (h.get('name') or h.get('title'), (h.get('first_air_date') or h.get('release_date') or 'Ano desconhecido')[:4], 'Filme' if h['media_type'] == 'movie' else 'Série') for h in hits]
    options = []
    for label, hit in zip(labels, hits):
        row = xbmcgui.ListItem(label=label, label2=hit.get('original_name') or hit.get('original_title', ''))
        from aniplay.metadata import get_image
        row.setArt({'thumb': get_image(hit, 'poster_path', 'w185')})
        options.append(row)
    choice = xbmcgui.Dialog().select('Selecionar a obra', options, useDetails=True)
    if choice >= 0:
        h = hits[choice]
        reference(q['url'], cache)
        with cache.user:
            cache.user.execute('INSERT OR REPLACE INTO tmdb_choice VALUES (?,?,?)', (slug(q['url']), h['media_type'], h['id']))
        with cache.db:
            cache.db.execute('DROP TABLE IF EXISTS episode_links')
        xbmc.executebuiltin('Container.Refresh')
    return


def handle_favorite():
    if action == 'favorite':
        library.save(cache.user, 'favorites', q['url'], q['title'], q.get('art', ''))
        if q.get('sources'):
            with cache.user:
                cache.user.execute('CREATE TABLE IF NOT EXISTS favorite_sources (url TEXT PRIMARY KEY, sources TEXT)')
                cache.user.execute('INSERT OR REPLACE INTO favorite_sources VALUES(?,?)', (q['url'], q['sources']))
        notification('Anime salvo', 'Minha lista', 'favorites')
    else:
        library.remove(cache.user, q['url'])
        notification('Anime removido', 'Minha lista', 'favorites')
        xbmc.executebuiltin('Container.Refresh')
    return


def handle_play():
    play()
    return


def handle_home():
    home()


def handle_continue():
    history = History(profile)
    rows = history.unfinished() if action == 'continue' else [(e, 0) for e in history.recently_watched()]
    for episode, offset in rows:
        title = episode['title']
        label = title + (' · %d:%02d' % divmod(int(offset), 60) if offset else '')
        params = {k: episode[k] for k in ('showid', 'season', 'local', 'raw', 'movie_id', 'show_url', 'show_title', 'episode_title', 'provider') if episode.get(k)}
        params.update(url=episode['url'], title=title, art=episode.get('icon', ''))
        item(label, 'play', params, art=params['art'])
    if not rows:
        item('Escolher um episódio', 'latest', icon='latest')


def handle_favorites():
    for url, title, art in library.contents(cache.user, action):
        route = 'show' if action == 'favorites' else 'play'
        from aniplay.metadata import lookup
        from aniplay.multisite import HOSTS, encode
        from urllib.parse import urlsplit
        site = next((key for key, host in HOSTS.items() if host == urlsplit(url).hostname), None)
        if action == 'favorites' and site and site != 'Bakashi':
            source = dict(site=site, title=title, url=url, imagem=art, audio='', season=None)
            cache.user.execute('CREATE TABLE IF NOT EXISTS favorite_sources (url TEXT PRIMARY KEY, sources TEXT)')
            saved = cache.user.execute('SELECT sources FROM favorite_sources WHERE url=?', (url,)).fetchone()
            item(title, 'multi_servers', dict(url=url, sources=saved[0] if saved else encode([source]), title=title, art=art),
                 data=lookup(title, cache, url, full=True), art=art)
        else:
            item(title, route, dict(url=url, title=title, art=art), art=art)
    if not views.listed:
        caption = 'Salvar animes pelo menu de contexto · Abrir catálogo' if action == 'favorites' else 'Escolher o primeiro episódio'
        item(caption, 'catalog' if action == 'favorites' else 'latest', icon='all' if action=='favorites' else 'latest')


def handle_search():
    search_menu()


def handle_filters():
    for field, label in [('genre', 'Gênero'), ('type', 'Formato'), ('year', 'Ano'), ('status', 'Status')]:
        item(label, 'filter', dict(field=field), icon={'genre': 'genre', 'year': 'year', 'type': 'format', 'status': 'status'}[field], info=dict(plot='Escolha uma opção de ' + label.lower() + ' para filtrar o catálogo.'))


def handle_filter():
    field = q['field']
    for value, label in filter_options(cache.get(BASE + '/lista-de-animes'), field):
        item(label, 'catalog', dict(url=BASE + '/lista-de-animes?' + urlencode({field: value})), icon='filters', info=dict(plot='Ver os animes deste filtro: ' + label + '.'))


def handle_catalog():
    if (action == 'query' and q.get('term')) or (action == 'catalog' and not q.get('url') and not q.get('offline')):
        from aniplay.multisite import browse
        if browse():
            return
    catalog()


def handle_multisite():
    from aniplay import multisite
    {'multi_catalog': multisite.browse, 'multi_servers': multisite.servers,
     'multi_seasons': multisite.seasons, 'multi_episodes': multisite.seasons}[action]()


def handle_show():
    series()


def handle_latest():
    from concurrent.futures import ThreadPoolExecutor
    from urllib.parse import urlsplit
    from aniplay.episode_context import cached, remember
    from aniplay.menu_metadata import catalog as catalog_records
    from aniplay.runtime import database, token
    from aniplay.titles import episode_title
    from source import Cache
    import re

    records = catalog_records()[0]
    def resolve(entry):
        params = dict(url=entry['url'], title=entry['name'], art=entry['art'], raw=entry['num'])
        return params, cached(params, include_stale=True)

    entries = [e for e in cards(cache.get(BASE + '/')) if '/ep/' in e['url']]
    items = [resolve(e) for e in entries]

    def fetch(pair):
        params, snapshot = pair
        if (snapshot and not snapshot.get('stale')) or not token:
            return None
        match = re.fullmatch(r'/ep/(.+)-(\d+)-episodio-[\d.,]+/?', urlsplit(params['url']).path)
        record = records.get(match[1]) if match else None
        if not record:
            return None
        db = Cache(database)
        try:
            return series(record[1], target=params['url'], preferred_season=match[2], db=db)
        except (OSError, ValueError):
            return None
        finally:
            db.user.close()
            db.db.close()

    with ThreadPoolExecutor(max_workers=5) as workers:
        resolved = list(workers.map(fetch, items))
        retry = [i for i, (params, snapshot) in enumerate(items)
                 if token and not snapshot and not (resolved[i] and resolved[i][1].get('id'))]
        for i, refreshed in zip(retry, workers.map(fetch, (items[i] for i in retry))):
            if refreshed and (not resolved[i] or refreshed[1].get('id')):
                resolved[i] = refreshed
    for e, (params, snapshot), found in zip(entries, items, resolved):
        if found and (found[1].get('id') or not (snapshot or {}).get('data', {}).get('id')):
            values, data, cast, fan = found
            params.update(values)
            with cache.db:
                remember(params, data, cast, fan)
            snapshot = dict(data=data, cast=cast, fan=fan)
        snapshot = snapshot or {}
        data = snapshot.get('data') or {'overview': e['plot']}
        site = re.sub(r'\s+' + re.escape(e['num']) + r'$', '', e['name']) if e['num'] else e['name']
        label = (params.get('episode_title') if params.get('movie_id') else
                 episode_title(params.get('raw'), params.get('episode_title'),
                               params.get('show_title') or site))
        params['title'] = label or e['name']
        item(params['title'], 'play', params, data=data, art=e['art'], cast=snapshot.get('cast'),
             fan=snapshot.get('fan', ''))


def handle_calendar():
    grouped = schedule(json.loads(cache.get(BASE + '/api/calendario', validate=json.loads))['days'])
    for date, entries in sorted(grouped.items()):
        day = date.isoformat()
        if action == 'calendar':
            label = '%s · %s (%d)' % (views.yellow(DAYS[date.weekday()]), date.strftime('%d/%m'), len(entries))
            item(label, 'calendar_day', dict(day=day), icon='day', info=dict(plot='Abrir a programação deste dia, em ordem de horário.'))
        elif day == q.get('day'):
            for (when, title, episode), entry in sorted(entries.items()):
                from aniplay.calendar_item import add
                add(when, title, episode or None, entry)


def handle_cast():
    from aniplay.info import directory
    directory()

ACTIONS = {
    'anime_info': handle_anime_info,
    'episode_info': handle_anime_info,
    'trailer': handle_anime_info,
    'export': handle_export,
    'purge': handle_purge,
    'prompt': handle_prompt,
    'person_prompt': handle_prompt,
    'edit_term': handle_prompt,
    'clear': handle_clear,
    'delete_term': handle_clear,
    'settings': handle_settings,
    'opening': handle_opening,
    'identify': handle_identify,
    'favorite': handle_favorite,
    'unfavorite': handle_favorite,
    'play': handle_play,
}

SCREENS = {
    'home': handle_home,
    'continue': handle_continue,
    'watched': handle_continue,
    'favorites': handle_favorites,
    'recent': handle_favorites,
    'search': handle_search,
    'filters': handle_filters,
    'filter': handle_filter,
    'catalog': handle_catalog,
    'multi_catalog': handle_multisite,
    'multi_servers': handle_multisite,
    'multi_seasons': handle_multisite,
    'multi_episodes': handle_multisite,
    'query': handle_catalog,
    'show': handle_show,
    'episodes': handle_show,
    'latest': handle_latest,
    'calendar': handle_calendar,
    'calendar_day': handle_calendar,
    'cast': handle_cast,
    'similar': handle_cast,
    'person': handle_cast,
    'people': handle_cast,
    'trending': handle_cast,
}
