"""Exporta referências estáveis aos episódios publicados no Bakashi."""
import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlsplit

import xbmcvfs

from aniplay.runtime import addon, profile


def write_episode(folder, params, season, number):
    root = addon.getSetting('library_path') or profile.rstrip('/\\') + '/Biblioteca'
    folder = root.rstrip('/\\') + '/' + safe(folder)
    directory = f'{folder}/Temporada {season:02d}'
    episode = f'S{season:02d}E{number.zfill(2)}' if number else safe(params['url'].split('/')[-1])
    write_stream(directory, episode, params)


def write_movie(title, params):
    root = addon.getSetting('library_path') or profile.rstrip('/\\') + '/Biblioteca'
    write_stream(root.rstrip('/\\') + '/Filmes', safe(title), params)


def write_stream(directory, name, params):
    if not xbmcvfs.exists(directory + '/') and not xbmcvfs.mkdirs(directory):
        raise OSError('Pasta de exportação indisponível')
    filename = f'{directory}/{name}.strm'
    suffix = hashlib.sha256(params['url'].encode()).hexdigest()[:16]
    alternate = f'{directory}/{name}-{suffix}.strm'
    if xbmcvfs.exists(alternate):
        filename = alternate
    elif xbmcvfs.exists(filename):
        with xbmcvfs.File(filename) as existing:
            previous = parse_qs(urlsplit(existing.read().strip()).query).get('url')
        if previous != [params['url']]:
            filename = alternate
    with xbmcvfs.File(filename, 'w') as stream:
        if not stream.write('plugin://plugin.video.aniplay.experimental/?' + urlencode(dict(action='play', **params)) + '\n'):
            raise OSError('Falha ao gravar episódio')


def safe(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value).strip(' .')[:100] or 'AniPlay'
