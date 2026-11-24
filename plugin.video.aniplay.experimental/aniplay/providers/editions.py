"""Correspondências verificadas nas listagens dos provedores e no TMDB."""
from urllib.parse import urlsplit

from aniplay.network import PROVIDER_HOSTS

# slug → (id TMDB, temporada TMDB, deslocamento, episódios regulares locais)
SEGMENTS = {
    'birdie-wing-golf-girls-story': (137390, 1, 0, 13),
    'birdie-wing-golf-girls-story-season-2': (137390, 1, 13, 12),
    'b6146d534fea1df93fb331751c95534c561b29bd': (82684, 2, 0, 12),
    'aaf08754be3b5dab97813591436ce7954c7c182c': (82684, 2, 12, 12),
    'tensei-shitara-slime-datta-ken-2nd-season-dublado': (82684, 2, 0, 12),
    'a772936b400fa5c4104ded7c503697d1dd080ad4': (82684, 2, 12, 12),
}
SEGMENT_PAIRS = (
    ('birdie-wing-golf-girls-story', 'birdie-wing-golf-girls-story-season-2'),
    ('b6146d534fea1df93fb331751c95534c561b29bd', 'aaf08754be3b5dab97813591436ce7954c7c182c'),
    ('tensei-shitara-slime-datta-ken-2nd-season-dublado', 'a772936b400fa5c4104ded7c503697d1dd080ad4'),
)
DIGIMON = '3ffe62e3b6aac35030469cf85cec7fd55bf2b726'
COSMOS = 'bishoujo-senshi-sailor-moon-cosmos-movie'
COSMOS_FILMS = {1: 968868, 2: 968870}
ONE_PIECE = {'e1eaa4181415abd4e16cce073629ee329ebd3200',
             '7804b6bdda34932920657ba29e64025244f485c7'}


def provider_slug(url):
    parts = urlsplit(url)
    if parts.scheme == 'https' and parts.hostname in PROVIDER_HOSTS:
        path = parts.path.strip('/').split('/')
        if len(path) == 2 and path[0] in ('anime', 'animes', 'anime-dublado', 'animes-dublado'):
            return path[1]
    return ''


def reference(url):
    key = provider_slug(url)
    segment = SEGMENTS.get(key)
    if segment:
        return 'tv', segment[0], segment[1]
    if key == DIGIMON:
        return 'tv', 31654, None
    if key in ONE_PIECE:
        return 'tv', 37854, None
    return None



def companion_segment(url):
    key = provider_slug(url)
    for first, second in SEGMENT_PAIRS:
        if key in (first, second):
            parts = urlsplit(url)
            prefix = parts.path.rstrip('/').rsplit('/', 1)[0]
            return parts._replace(path=prefix + '/' + (second if key == first else first),
                                  query='', fragment='').geturl()
    return ''
