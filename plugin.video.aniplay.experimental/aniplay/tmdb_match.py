import re
import unicodedata
from functools import lru_cache
from aniplay.data_files import load as load_data
from aniplay.titles import clean_text, show_title
from urllib.parse import urlsplit


def normalized(title):
    folded = unicodedata.normalize('NFKD', clean_text(title).casefold())
    return ' '.join(re.findall(r'[^\W_]+', ''.join(c for c in folded if not unicodedata.combining(c))))


def slug(url):
    return re.sub(r'-\d+a-temporada$', '', urlsplit(url).path.rstrip('/').split('/')[-1])


@lru_cache(maxsize=1)
def index():
    return load_data('tmdb-index.json')



def catalog_title(site, data, url, original=False):
    key = slug(url)
    match = index().get(key)
    if match and data.get('id') == match[1] and (match[2] not in (None, 1) or key in editions()):
        site = clean_text(site)
        if site and not original:
            return site
        preferred = show_title(site, data, original)
        if site and normalized(preferred) != normalized(site) and normalized(site) not in normalized(preferred):
            return f'{preferred} · {site}'
        return preferred
    return show_title(site, data, original)


def unique_hit(name, hits):
    target = normalized(name)
    matches = [h for h in hits if h.get('media_type') in ('movie','tv') and
               any(normalized(h.get(k) or '') == target for k in ('name','title','original_name','original_title'))]
    animated = [h for h in matches if 16 in h.get('genre_ids',[])]
    candidates = animated or matches
    return candidates[0] if len(candidates) == 1 else {}


def title_variants(title):
    import html
    text = html.unescape(title).strip()
    parts = [text]
    for alternate in re.findall(r'\(([^()]+)\)', text):
        if re.search(r'[^\d\W]', alternate):
            parts.append(alternate)
    parts.append(re.sub(r'\s*\([^()]+\)|\s+(?:19|20)\d\d$', '', text).strip())
    return list(dict.fromkeys(p for p in parts if p))


def dated_hit(titles, hits, year):
    keys = {normalized(name) for name in titles}
    exact = [h for h in hits if 16 in h.get('genre_ids',[]) and
             (h.get('first_air_date') or h.get('release_date') or '')[:4] == year and
             any(normalized(h.get(k) or '') in keys for k in ('name','original_name','title','original_title'))]
    return exact[0] if len(exact)==1 else {}


@lru_cache(maxsize=1)
def editions():
    return load_data('editions.json')


@lru_cache(maxsize=1)
def bakashi_metadata():
    return load_data('bakashi-metadata.json')
