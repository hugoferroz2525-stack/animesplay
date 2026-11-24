"""Seleção de legendas externas pela API REST do OpenSubtitles."""
import json
import os
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

API = 'https://api.opensubtitles.com/api/v1/'


def query(params, language):
    if str(params.get('movie_id', '')).isdigit():
        return dict(type='movie', tmdb_id=params['movie_id'], languages=language)
    if all(str(params.get(k, '')).isdigit() for k in ('showid', 'season', 'local')):
        return dict(type='episode', parent_tmdb_id=params['showid'], season_number=params['season'],
                    episode_number=params['local'], languages=language)
    return {}


def request(endpoint, headers, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    with urlopen(Request(API + endpoint, data=body, headers=headers), timeout=10) as response:
        return json.load(response)


def selector_options(results):
    options = []
    for row in results:
        attributes = row['attributes']
        details = []
        try:
            rating = float(attributes.get('ratings'))
        except (ValueError, TypeError):
            rating = 0
        if 0 < rating <= 10:
            details.append(('Nota %g/10' % rating).replace('.', ','))
        if attributes.get('hearing_impaired') is True:
            details.append('Com descrição de sons')
        for entry in attributes['files']:
            if str(entry.get('file_id', '')).isdigit():
                file_id = int(entry['file_id'])
                name = entry.get('file_name') or attributes.get('release') or str(file_id)
                options.append((file_id, ' · '.join(details + [name])))
    return options


def select_file(params, addon, profile, select):
    search = query(params, addon.getSetting('subtitle_language') or 'pt-br')
    if not search:
        raise ValueError('Falta a identificação desta obra ou episódio no TMDB.')
    key = addon.getSetting('subtitle_key').strip()
    if not key:
        raise ValueError('Configure a chave do OpenSubtitles nas opções de Legendas.')
    headers = {'Api-Key': key, 'User-Agent': 'AniPlay v' + addon.getAddonInfo('version'),
               'Content-Type': 'application/json', 'Accept': 'application/json'}
    results = request('subtitles?' + urlencode(search), headers)
    options = selector_options(results['data'])
    if not options:
        raise ValueError('Nenhuma legenda encontrada no idioma escolhido.')
    index = select('OpenSubtitles', ['Continuar sem legenda externa'] +
                   [label for _, label in options])
    if index <= 0:
        return
    file_id = options[index - 1][0]
    folder = Path(profile) / 'subtitles'
    folder.mkdir(exist_ok=True)
    language = search['languages']
    # Kodi interpreta o último sufixo como idioma ISO, inclusive em pt-br.
    kodi_language = {'pt-br': 'por', 'pt-pt': 'por'}.get(language, language)
    target = folder / ('%d_%s.%s.srt' % (file_id, language, kodi_language))
    legacy = folder / ('%d.%s.srt' % (file_id, language))
    if legacy.is_file() and not target.exists():
        try:
            legacy.replace(target)
        except FileNotFoundError:
            pass
    if target.is_file():
        return str(target)
    user = addon.getSetting('subtitle_user').strip()
    if user:
        session = request('login', headers, dict(username=user, password=addon.getSetting('subtitle_password')))
        headers['Authorization'] = 'Bearer ' + session['token']
    link = request('download', headers, dict(file_id=file_id, sub_format='srt'))['link']
    if urlsplit(link).scheme != 'https':
        raise ValueError('O serviço devolveu um endereço de download inválido.')
    with urlopen(link, timeout=15) as response:
        data = response.read(8_000_001)
    if len(data) > 8_000_000 or b'-->' not in data:
        raise ValueError('O arquivo recebido não contém uma legenda SRT válida.')
    with tempfile.NamedTemporaryFile(dir=folder, delete=False) as temp:
        try:
            temp.write(data)
            temp.close()
            os.replace(temp.name, target)
        finally:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
    return str(target)


def attach(item, params, addon, profile):
    if not addon.getSettingBool('external_subtitles'):
        return
    import xbmcgui
    from aniplay.flix_ui import notification
    try:
        path = select_file(params, addon, profile, xbmcgui.Dialog().select)
        if path:
            item.setSubtitles([path])
    except HTTPError as exc:
        message = {401: 'Verifique a chave e os dados da conta.', 403: 'Acesso recusado pelo OpenSubtitles.',
                   406: 'Cota de downloads atingida.', 429: 'Limite de consultas atingido.'}
        notification(message.get(exc.code, 'Falha HTTP %d.' % exc.code), 'OpenSubtitles', 'sub')
    except (OSError, KeyError, TypeError, ValueError) as exc:
        message = str(exc) if type(exc) is ValueError else 'Falha ao consultar ou salvar a legenda.'
        notification(message, 'OpenSubtitles', 'sub')
