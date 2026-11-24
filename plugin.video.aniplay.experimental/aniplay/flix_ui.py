"""Utilidades adaptadas de Flix/lib/tmdb.py e lib/api/flix/kodi.py (MIT)."""
from pathlib import Path
import xbmcgui
from aniplay.titles import clean_text

ART = Path(__file__).resolve().parent.parent / 'resources' / 'icons'


def notification(message, heading='AniPlay', icon='play', time=3500, sound=False):
    xbmcgui.Dialog().notification('[COLOR FFFFD32D]'+heading+'[/COLOR]',message,str(ART/(icon+'.png')),time,sound)


def get_cast(credits):
    people = {}
    for credit in credits:
        name = clean_text(credit.get('name')) or clean_text(credit.get('original_name'))
        if not name:
            continue
        ident = credit.get('id')
        person = people.setdefault(ident or name, dict(id=ident, name=name, roles=[], thumbnail=''))
        role = clean_text(credit.get('character'))
        if role and role not in person['roles']:
            person['roles'].append(role)
        path = credit.get('profile_path')
        if isinstance(path, str) and path.startswith('/') and not person['thumbnail']:
            person['thumbnail'] = 'https://image.tmdb.org/t/p/w342' + path
    for person in people.values():
        person['role'] = ' / '.join(person.pop('roles'))
    return list(people.values())


def directors(crew):
    return list(dict.fromkeys(clean_text(c.get('name')) for c in crew
                              if c.get('job') == 'Director' and clean_text(c.get('name'))))


def writers(crew):
    return list(dict.fromkeys(clean_text(c.get('name')) for c in crew
                              if (c.get('department') == 'Writing' or c.get('job') == 'Writer')
                              and clean_text(c.get('name'))))
