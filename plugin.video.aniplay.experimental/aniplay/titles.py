"""Rótulos para o Kodi. O número publicado continua separado do número do TMDB."""
from html import unescape
import re
from unicodedata import normalize


def clean_text(value):
    return normalize('NFC', unescape(value)).strip() if isinstance(value, str) else ''


def show_title(site, data, original=False):
    site = clean_text(site)
    title = clean_text(data.get('original_name') if original else None) or clean_text(data.get('name')) or site
    edition = re.search(r'\b(dublad[oa]|legendad[oa]|director.s cut|versão do diretor)\b', site, re.I)
    year = re.search(r'(?:^|[ (])((?:19|20)\d{2})\)?$', site)
    if year and not re.search(r'\b' + year[1] + r'\b', title):
        title += ' (' + year[1] + ')'
    if edition and edition[0].casefold() not in title.casefold():
        title += ' · ' + edition[0]
    return title


def season_title(number, name, fallback):
    if fallback in ('Especiais', 'Filmes', 'Filme', 'Coleção', 'Outros episódios'):
        return fallback
    name = clean_text(name)
    base = f'Temporada {number}'
    generic = not name or re.fullmatch(r'(?:temporada|season)\s*\d+', name.strip(), re.I)
    return base if generic else f'{base} · {name}'


def episode_title(number, title, series=''):
    title = clean_text(title)
    series = clean_text(series)
    number = str(number or '')
    if number.isdigit():
        number = f'{int(number):02d}'
    heading = f'Episódio {number}' if number else ''
    if heading and re.fullmatch(r'(?:episódio|episode)\s+\d+', title, re.I):
        title = ''
    return ' · '.join(part for part in (series, heading, title) if part)



def highlight_episode_title(label, title, highlight):
    title = clean_text(title)
    if not title or re.fullmatch(r'(?:episódio|episode)\s+[\d.,]+', title, re.I):
        return label
    progress = re.search(r' · \d+:\d{2}$', label)
    end = len(label)
    if not (label == title or label.endswith(' · ' + title)) and progress:
        end = progress.start()
    heading = label[:end]
    if heading == title or heading.endswith(' · ' + title):
        return heading[:-len(title)] + highlight(title) + label[end:]
    return label
