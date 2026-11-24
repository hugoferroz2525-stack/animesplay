"""Compose TMDB rating badges on local poster copies."""
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
import os
import re
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request
from urllib.error import HTTPError

from aniplay.network import CheckedOpener, PROVIDER_HOSTS

HOST = 'image.tmdb.org'
SITE_ART_HOST = 'anidb.00000120.xyz'
MAX_IMAGE_BYTES = 4 * 1024 * 1024
CACHE_LIMIT = 384
STYLE = 'tmdb-corner-v2'


@lru_cache(maxsize=1)
def pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
        font(16, ImageFont)
        if not hasattr(ImageDraw.ImageDraw, 'textlength') or not hasattr(ImageDraw.ImageDraw, 'rounded_rectangle'):
            return None
        return Image, ImageDraw, ImageFont
    except (ImportError, OSError, TypeError):
        return None


def font(size, module):
    font_path = Path(__file__).resolve().parents[1] / 'resources' / 'fonts' / 'DejaVuSans.ttf'
    return module.truetype(str(font_path), size)


def poster_cache(profile):
    return Path(profile) / 'poster-badges'


def valid_poster(url, badge=''):
    if url == 'default':
        return bool(badge)
    parts = urlsplit(url)
    path = (parts.netloc == HOST and parts.path.startswith('/t/p/')) or (
        badge and ((parts.netloc == SITE_ART_HOST and parts.path.startswith('/content/animes/posters/'))
                   or parts.netloc in PROVIDER_HOSTS))
    return bool(parts.scheme == 'https' and path and not parts.query and not parts.fragment)


def get_poster(profile, url, rating, votes=None, badge=''):
    """Return a finished poster or enqueue it for the Kodi service."""
    if badge and not re.fullmatch(r'Servidor [1-9]\d?', badge):
        return ''
    if not valid_poster(url, badge):
        if not badge:
            return ''
        url = 'default'
    score = (f'{rating:.1f}'.replace('.', ',')
             if isinstance(rating, (int, float)) and 0 < rating <= 10 and votes != 0 else '')
    if not score and not badge:
        return ''
    identity = f'{STYLE}\n{url}\n{score}' + (f'\n{badge}' if badge else '')
    key = sha256(identity.encode()).hexdigest()
    folder = poster_cache(profile)
    poster = folder / f'{key}.jpg'
    if poster.is_file():
        return str(poster)
    if poster.with_suffix('.skip').is_file() or not pillow():
        return ''
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / f'{key}.job').open('x', encoding='utf-8') as job:
            json.dump((url, score, badge), job)
    except OSError:
        pass
    return ''


def render(data, score, target, badge=''):
    Image, ImageDraw, ImageFont = pillow()
    with Image.open(BytesIO(data)) as source:
        if source.width * source.height > 6_000_000 or source.width < 120:
            raise ValueError('Invalid poster dimensions')
        source.thumbnail((500, 900), getattr(Image, 'Resampling', Image).LANCZOS)
        poster = source.convert('RGBA')
    overlay = Image.new('RGBA', poster.size)
    draw = ImageDraw.Draw(overlay)
    height = max(28, round(poster.width * .106))
    padding = round(height * .25)
    if badge:
        badge_font = font(round(height * .47), ImageFont)
        width = round(draw.textlength(badge, font=badge_font)) + 2 * padding
        x, y = padding, padding
        draw.rounded_rectangle((x, y, x + width, y + height), radius=round(height * .22),
                               fill=(13, 16, 20, 239), outline=(255, 255, 255, 75), width=1)
        draw.text((x + padding, y + height / 2), badge, font=badge_font, anchor='lm', fill=(255, 211, 45))
    if score:
        mark_font = font(round(height * .34), ImageFont)
        score_font = font(round(height * .55), ImageFont)
        mark_width = round(draw.textlength('TMDB', font=mark_font))
        width = mark_width + round(draw.textlength(score, font=score_font)) + 4 * padding
        x, y = poster.width - padding - width, padding
        draw.rounded_rectangle((x, y, x + width, y + height), radius=round(height * .22),
                               fill=(13, 16, 20, 239), outline=(255, 255, 255, 75), width=1)
        middle = y + height / 2
        draw.text((x + padding, middle), 'TMDB', font=mark_font, anchor='lm', fill=(137, 225, 191))
        divider = x + mark_width + 2 * padding
        draw.line((divider, y + padding, divider, y + height - padding),
                  fill=(255, 255, 255, 85), width=1)
        draw.text((divider + padding, middle), score, font=score_font, anchor='lm', fill=(255, 211, 45))
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
        temporary = Path(temp.name)
        try:
            Image.alpha_composite(poster, overlay).convert('RGB').save(temp, 'JPEG', quality=92)
            temp.close()
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def pending_job(profile, exclude=()):
    folder = poster_cache(profile)
    now = time.time()
    try:
        return min((job for job in folder.glob('*.job') if job not in exclude and job.stat().st_mtime <= now),
                   key=lambda job: job.stat().st_mtime, default=None)
    except OSError:
        return None


def process(job):
    target = job.with_suffix('.jpg')
    try:
        if not target.is_file():
            url, score, *parts = json.loads(job.read_text(encoding='utf-8'))
            badge = parts[0] if parts else ''
            valid_score = isinstance(score, str) and (not score or bool(re.fullmatch(r'(?:[0-9]|10),[0-9]', score)))
            valid_badge = isinstance(badge, str) and (not badge or bool(re.fullmatch(r'Servidor [1-9]\d?', badge)))
            if not valid_score or not valid_badge or not valid_poster(url, badge) or not (score or badge):
                raise ValueError('Invalid poster job')
            if url == 'default':
                data = (Path(__file__).resolve().parents[1] / 'icon.png').read_bytes()
            else:
                try:
                    with CheckedOpener(urlsplit(url).hostname).open(Request(url), timeout=5) as response:
                        data = response.read(MAX_IMAGE_BYTES + 1)
                except HTTPError as error:
                    if error.code not in (408, 429) and error.code < 500:
                        raise ValueError('Poster unavailable') from error
                    raise
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError('Poster exceeds size limit')
            try:
                render(data, score, target, badge)
            except pillow()[0].UnidentifiedImageError as error:
                raise ValueError('Invalid image') from error
        job.unlink(missing_ok=True)
        posters = sorted(job.parent.glob('*.jpg'), key=lambda poster: poster.stat().st_mtime)
        for old in posters[:-CACHE_LIMIT]:
            old.unlink(missing_ok=True)
    except (ValueError, TypeError):
        job.replace(job.with_suffix('.skip'))
    except OSError:
        try:
            retry = time.time() + 300
            os.utime(job, (retry, retry))
        except OSError:
            pass
