"""Agrupa obras preservando a origem, a edição de áudio e a temporada."""
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlsplit, unquote


AUDIO = re.compile(r'\b(dublad[oa]|legendad[oa]|dub|sub)\b', re.I)
SEASON = re.compile(
    r'(?:(?:temporada|season)\s+(\d+)|(\d+)\s*(?:[ªºoa]|st|nd|rd|th)?\s*(?:temporada|season)|\bs(\d+))$',
    re.I,
)


def identity(title, url):
    title = re.sub(r'^\s*assistir\s+|\s+online\s*$', '', title, flags=re.I)
    audio = AUDIO.search(title)
    path = unquote(urlsplit(url).path).rstrip('/')
    if not audio:
        audio = AUDIO.search(path.rsplit('/', 1)[-1].replace('-', ' '))
    language = ('Dublado' if audio[1].lower().startswith('dub') else 'Legendado') if audio else ''
    if not language and path.startswith(('/anime-dublado/', '/animes-dublado/')):
        language = 'Dublado'
    base = AUDIO.sub('', title).strip(' -·:[]()')
    season = SEASON.search(base)
    hint = None
    if season:
        hint = int(next(value for value in season.groups() if value is not None))
        base = base[:season.start()].rstrip(' -·:[]()')
    if hint is None:
        hint = re.search(r'-(\d+)a-temporada/?$', urlsplit(url).path)
        hint = int(hint[1]) if hint and int(hint[1]) > 1 else None
    return base or title, language, hint


def chave_titulo(titulo):
    folded = unicodedata.normalize('NFKD', titulo.casefold())
    folded = ''.join(c for c in folded if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w]+', ' ', folded).split())


@dataclass
class AnimeAgrupado:
    titulo: str
    fontes: list = field(default_factory=list)
    key: str = ''


def agrupar_animes(resultados, identities=None):
    identities = identities or {}
    prepared, aliases = [], {}
    for site, title, url, art in resultados:
        base, audio, season = identity(title, url)
        key = chave_titulo(base)
        if not key or not url:
            continue
        known = identities.get(url)
        if known:
            aliases.setdefault(key, set()).add(known)
        prepared.append((key, base, known, dict(site=site, title=title, url=url, imagem=art,
                                                audio=audio, season=season)))
    groups = {}
    for key, base, known, source in prepared:
        choices = aliases.get(key, ())
        identity_key = known or (next(iter(choices)) if len(choices) == 1 else 'title:' + key)
        group = groups.setdefault(identity_key, AnimeAgrupado(base, key=identity_key))
        if not any(item['site'] == source['site'] and item['url'] == source['url'] for item in group.fontes):
            group.fontes.append(source)
    return list(groups.values())
