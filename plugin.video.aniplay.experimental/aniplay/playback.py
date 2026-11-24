from aniplay.flix_ui import notification
from aniplay.opening import saved
import xbmc
import xbmcgui
import xbmcplugin
from source import audio_sources, player_buttons
from source import UA, media
from aniplay.tmdb_match import slug
import re
from urllib.parse import urlencode
from aniplay.validation import probe_media
from aniplay.runtime import addon, cache, handle, q
from aniplay.storage.history import History, PENDING, media_key
from aniplay.runtime import profile
import json
from aniplay.data_files import load as load_data
import sys
import time

def skip_mode():
    value = addon.getSetting('skip_mode').strip().lower()
    if value.startswith('deslig'):
        return 'off'
    if value.startswith('auto'):
        return 'auto'
    return 'button'


def choose_other_audio(audio, alternatives):
    if alternatives:
        choice = xbmcgui.Dialog().select(
            f'{audio} indisponível. Escolha outro áudio ou cancele.', alternatives)
        if choice >= 0:
            return alternatives.pop(choice)
    else:
        notification(f'{audio} indisponível para este episódio.', 'Áudio indisponível', 'alert')
    return None


def resolve_audio(groups, audio, names):
    failures = []
    while True:
        for frame in groups[audio]:
            try:
                stream,markers = media(frame,q['url'],cache)
                mime = probe_media(stream,frame)
                break
            except (OSError,ValueError) as exc:
                reason = getattr(exc, 'code', type(exc).__name__)
                failures.append(reason)
                xbmc.log('AniPlay: fonte %s · %s' % (audio, reason), xbmc.LOGWARNING)
                continue
        else:
            if names:
                audio = choose_other_audio(audio, names)
                if audio:
                    continue
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
                return
            refused = failures and all(code in ('source_denied', 'http_401', 'http_403', 'hls_http_401', 'hls_http_403', 401, 403) for code in failures)
            message = 'O servidor recusou o acesso ao vídeo.' if refused else 'O servidor não entregou um vídeo reproduzível.'
            notification(message, heading='Fonte indisponível', icon='alert')
            xbmcplugin.setResolvedUrl(handle,False,xbmcgui.ListItem())
            return
        break
    return audio,stream,markers,mime,frame


def stream_item(stream, mime, frame, extra_headers=None):
    values = {'Referer': frame, 'User-Agent': UA, 'Accept': '*/*'}
    values.update(extra_headers or {})
    headers = urlencode(values)
    li = xbmcgui.ListItem(path=stream+'|'+headers)
    if mime == 'application/vnd.apple.mpegurl':
        li.setPath(stream)
        li.setProperty('inputstream','inputstream.adaptive')
        if int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0]) < 21:
            li.setProperty('inputstream.adaptive.manifest_type','hls')
        li.setProperty('inputstream.adaptive.manifest_headers',headers)
        li.setProperty('inputstream.adaptive.stream_headers',headers)
        li.setMimeType('application/vnd.apple.mpegurl')
        li.setContentLookup(False)
    return li


def play():
    from urllib.parse import urlsplit
    from aniplay.network import PROVIDER_HOSTS
    if q.get('audio_options') or q.get('audio_parents'):
        from aniplay.multisite import select_bakashi_edition, select_external_audio
        selected = select_external_audio() if q.get('audio_options') else select_bakashi_edition()
        if not selected:
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
    if urlsplit(q['url']).hostname in PROVIDER_HOSTS:
        return play_provider()
    body = cache.get(q['url'])
    groups = audio_sources(body,q['url'])
    requested = q.get('preferred_audio')
    if not groups and not requested:
        raise ValueError('Este episódio está sem player disponível.')
    names = list(groups)
    show_key = slug(q['show_url']) if q.get('show_url') else re.sub(r'-[0-9]+-episodio-.*$', '',slug(q['url']))
    remember = addon.getSettingBool('remember_audio')
    cache.user.execute('CREATE TABLE IF NOT EXISTS audio_preferences (anime TEXT PRIMARY KEY, audio TEXT)')
    preferred = cache.user.execute('SELECT audio FROM audio_preferences WHERE anime=?',(show_key,)).fetchone() if remember else None
    if requested and requested not in names:
        audio = choose_other_audio(requested, names)
        if not audio:
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
    elif requested:
        audio = names.pop(names.index(requested))
    elif len(names)>1:
        choice = xbmcgui.Dialog().select('Como quer assistir?',names,preselect=names.index(preferred[0]) if preferred and preferred[0] in names else -1)
        if choice < 0:
            xbmcplugin.setResolvedUrl(handle,False,xbmcgui.ListItem())
            return
        audio = names.pop(choice)
    else:
        audio = names.pop(0)

    from aniplay.providers.scraper import quality_label
    from aniplay.views import yellow
    qualities = {frame: quality_label(label) for language, label, frame in player_buttons(body, q['url'])
                 if language == audio and quality_label(label)}
    frames = list(qualities)
    if len(set(qualities.values())) > 1:
        choice = xbmcgui.Dialog().select('Qualidade', ['Automática'] + [yellow(qualities[frame]) for frame in frames])
        if choice < 0:
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
        if choice:
            groups[audio] = [frames[choice - 1]]
    resolved=resolve_audio(groups,audio,names)
    if not resolved:
        return
    finish_playback(*resolved, remember=remember, show_key=show_key)


def play_provider():
    from aniplay.multisite import HOSTS, check_source, source_log
    from aniplay.providers.scraper import Resolver, ScraperError, NoPlayerMedia, quality_choices, quality_label, mp4_height
    from aniplay.views import yellow
    from urllib.parse import urlsplit

    site = next((name for name, host in HOSTS.items()
                 if urlsplit(q['url']).hostname == host), '')
    check_source(site, q['url'])
    q['provider'] = site
    resolver = Resolver(timeout=8)
    started = time.monotonic()
    try:
        page = resolver.episode_page(q['url'])
        choices = quality_choices(page)
        if choices:
            labels = []
            keys = []
            for label, kind, value in choices:
                key = 'quality:' + json.dumps([page.url, kind, value])
                keys.append(key)
                saved = cache.db.execute('SELECT body FROM pages WHERE id=? AND stamp>?',
                                         (key, time.time()-86400)).fetchone()
                labels.append(label if quality_label(label) or not saved else saved[0])
            unknown = [i for i, label in enumerate(labels) if not quality_label(label)]
            menu = [yellow(label) if quality_label(label) else label for label in labels]
            if unknown and len(choices) > 1:
                menu.append('Identificar resoluções')
            choice = xbmcgui.Dialog().select('Qualidade ou player · ' + site, menu) if len(choices) > 1 else 0
            if choice == len(choices):
                for i in unknown:
                    _, kind, value = choices[i]
                    try:
                        stream = (resolver._validate(value, page.url, '', value) if kind == 'source'
                                  else resolver.get_player(page, value)['stream'])
                        height = mp4_height(resolver, stream)
                    except (OSError, ScraperError):
                        continue
                    if height:
                        labels[i] = f'{height}p'
                        with cache.db:
                            cache.db.execute('INSERT OR REPLACE INTO pages VALUES(?,?,?)',
                                             (keys[i], time.time(), labels[i]))
                cache.trim_cache()
                choice = xbmcgui.Dialog().select('Qualidade ou player · ' + site, [
                    yellow(label) if quality_label(label) else label for label in labels])
            if choice < 0:
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
                return
            _, kind, value = choices[choice]
            if kind == 'source':
                stream = resolver._validate(value, page.url, '', value)
            else:
                stream = resolver.get_player(page, value)['stream']
        else:
            stream = resolver.get_player(page)['stream']
    except ScraperError as exc:
        source_log(site, 'player', started, error=exc)
        message = ('O player abriu, mas não enviou uma fonte de vídeo reconhecível. '
                   'Tente outro player ou servidor.' if isinstance(exc, NoPlayerMedia) else str(exc))
        notification(message, site, 'alert')
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return
    source_log(site, 'midia_validada', started, 'rede', 1)
    _, content_type = resolver.verification
    mime = ('application/vnd.apple.mpegurl' if 'mpegurl' in content_type
            or urlsplit(stream).path.lower().endswith('.m3u8') else 'video/mp4')
    finish_playback(site, stream, (), mime, resolver.referer, headers=resolver.headers)


def finish_playback(audio, stream, markers, mime, frame, *, headers=None, remember=False, show_key=''):
    from aniplay.episode_context import restore
    snapshot = {}
    try:
        snapshot = restore(q)
    except (OSError, ValueError, KeyError):
        xbmc.log('AniPlay: metadados do episódio indisponíveis', xbmc.LOGWARNING)
    if not q.get('provider'):
        notification(audio,'Áudio selecionado','dub' if 'dubl' in audio.lower() else 'sub')
    li=stream_item(stream,mime,frame,headers)
    episode = dict(id=q['url'], url=q['url'], title=q.get('title') or q['url'].split('/')[-1],
                   icon=q.get('art',''), audio=audio)
    episode.update({k:q[k] for k in ('showid','season','local','raw','movie_id','show_url','show_title','episode_title','provider') if q.get(k)})
    offset = History(profile).resume(episode['id'])
    if offset:
        choice = xbmcgui.Dialog().select('Reprodução', [
            'Continuar de %d:%02d' % divmod(int(offset),60), 'Ver desde o início'])
        if choice < 0:
            xbmcplugin.setResolvedUrl(handle,False,xbmcgui.ListItem())
            return
        if choice == 1:
            offset = 0
    from aniplay.subtitles import attach
    attach(li, q, addon, profile)
    markers = saved(cache.user,q['url']) or markers
    mode = skip_mode()
    intervals = []
    if markers and mode != 'off' and 0 <= markers[0] < markers[1]:
        intervals.append(('op', *markers))
    pending = dict(skip_enabled=mode != 'off',skip_mode=mode,keys=[media_key(stream), media_key(sys.argv[0]+sys.argv[2])],
                   expires=time.time()+120, item=episode, resume=offset, skip=intervals)
    if mode != 'off':
        ids = load_data('aniskip-ids.json')
        show_id = q.get('showid','')
        absolute_id = ids.get(show_id+'/absolute')
        mal = absolute_id or ids.get(show_id+'/'+q.get('season',''))
        number = q.get('raw' if absolute_id else 'local','')
        if mal and number.isdigit():
            pending['aniskip'] = [mal,int(number)]
            pending['allowed'] = ['op'] + (['ed'] if addon.getSettingBool('skip_end') else [])
    if remember:
        with cache.user:
            cache.user.execute('INSERT OR REPLACE INTO audio_preferences VALUES (?,?)',(show_key,audio))
    from aniplay import videotag
    data = snapshot.get('data', {})
    title = data.get('name') or q.get('episode_title') or q.get('title') or episode['title']
    videotag.decorate(li, data, title=title, fields=videotag.episode_fields(q),
                     art=q.get('art', ''), fan=snapshot.get('fan', ''),
                     cast_override=snapshot.get('cast'))
    xbmcgui.Window(10000).setProperty(PENDING,json.dumps(pending))
    xbmcplugin.setResolvedUrl(handle,True,li)
    return
