# -*- coding: utf-8 -*-
import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from html.parser import HTMLParser
from http.client import HTTPException
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree


base = 'https://www.hinatasoul.com'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0'
VOID_TAGS = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
MEDIA_SUFFIXES = ('.mp4', '.m3u8')
TIMEOUT = 15
PLAYER_ORDER = ('2', '1', '0')
AD_DOMAINS = ('2mdn.net', 'doubleclick.net', 'googlesyndication.com',
              'googleadservices.com', 'adnxs.com', 'imasdk.googleapis.com',
              'adsrvr.org', 'adform.net', 'spotxchange.com')
AD_PATH = r'(?:^|/)(?:web_video_ads|video_ads|vast|vpaid|preroll|ads?|advertising)(?:/|[._-]|$)'
PLAYBACK_HEADERS = ('User-Agent', 'Referer', 'Cookie', 'Origin', 'Authorization')
LOG = logging.getLogger(__name__)


class ScraperError(Exception):
    pass


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    contents: list = field(default_factory=list)

    def find_all(self, tag, *classes, element_id=None):
        for child in self.contents:
            if isinstance(child, Node):
                if (child.tag == tag
                        and all(name in child.attrs.get('class', '').split() for name in classes)
                        and (element_id is None or child.attrs.get('id') == element_id)):
                    yield child
                yield from child.find_all(tag, *classes, element_id=element_id)

    def find(self, tag, *classes, element_id=None):
        return next(self.find_all(tag, *classes, element_id=element_id), None)

    def text(self):
        return ''.join(part.text() if isinstance(part, Node) else part for part in self.contents).strip()


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node('document')
        self.stack = [self.root]
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {name: value or '' for name, value in attrs})
        self.stack[-1].contents.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].contents.append(Node(tag, {name: value or '' for name, value in attrs}))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].contents.append(data)


@dataclass
class Page:
    url: str
    text: str
    media: bool = False


def http_url(value, source=''):
    if value:
        try:
            url = urljoin(source, value.strip())
            parts = urlsplit(url)
            if (parts.scheme in ('http', 'https') and parts.hostname
                    and parts.username is None and parts.password is None
                    and not re.search(r'[\x00-\x20\x7f|]', url)):
                return url
        except ValueError:
            return ''
    return ''


def media_url(url):
    return bool(url and urlsplit(url).path.lower().endswith(MEDIA_SUFFIXES))


def media_type(headers):
    content_type = headers.get_content_type()
    return content_type.startswith('video/') or content_type in (
        'application/vnd.apple.mpegurl', 'application/x-mpegurl', 'audio/mpegurl',
    )


def is_ad(url):
    parts = urlsplit(url)
    host = (parts.hostname or '').rstrip('.').lower()
    return (any(host == domain or host.endswith('.' + domain) for domain in AD_DOMAINS)
            or bool(re.search(AD_PATH, unquote(parts.path), re.IGNORECASE)))


def episode_id(url):
    match = re.match(r'^/videos?/(\d+)(?:/|$)', urlsplit(url).path)
    return match[1] if match else ''


def is_episode_media(url, identifier, declared=''):
    if not http_url(url) or is_ad(url):
        return False
    filename = unquote(urlsplit(url).path).rsplit('/', 1)[-1].lower()
    return bool(url == declared or (identifier and
                filename in (identifier + '.mp4', identifier + '.m3u8')))


def check_authorization(url):
    parts = urlsplit(url)
    query = {key.lower(): values for key, values in parse_qs(parts.query).items()}
    signature = query.get('x-amz-signature')
    host = parts.hostname.rstrip('.').lower()
    if (host == 'r2.cloudflarestorage.com' or host.endswith('.r2.cloudflarestorage.com')) and not signature:
        raise ScraperError('URL do Cloudflare R2 sem assinatura temporária.')
    if signature:
        try:
            date = datetime.strptime(query['x-amz-date'][0], '%Y%m%dT%H%M%SZ')
            expires = int(query['x-amz-expires'][0])
            deadline = date.replace(tzinfo=timezone.utc) + timedelta(seconds=expires)
        except (KeyError, ValueError, OverflowError):
            raise ScraperError('Prazo da assinatura temporária inválido.') from None
        if expires <= 0 or deadline <= datetime.now(timezone.utc):
            raise ScraperError('A assinatura temporária da mídia expirou.')


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not http_url(newurl) or is_ad(newurl):
            raise ScraperError('Redirecionamento inválido ou publicitário (HTTP {}).'.format(code))
        LOG.info('Redirecionamento HTTP %s de %s para %s.', code,
                 urlsplit(req.full_url).hostname, urlsplit(newurl).hostname)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urlsplit(req.full_url)[:2] != urlsplit(newurl)[:2]:
            for header in ('Authorization', 'Cookie', 'Origin', 'Referer'):
                redirected.remove_header(header)
        return redirected


class Client:
    def __init__(self, timeout=TIMEOUT):
        self.cookies = CookieJar()
        self.opener = build_opener(SafeRedirect(), HTTPCookieProcessor(self.cookies))
        self.timeout = timeout

    def playback_headers(self, url, referer):
        request = Request(url)
        self.cookies.add_cookie_header(request)
        headers = {'User-Agent': USER_AGENT}
        if referer:
            headers['Referer'] = referer
        if request.has_header('Cookie'):
            headers['Cookie'] = request.get_header('Cookie')
        return headers

    def open(self, url, referer='', first_bytes=False, extra_headers=None):
        url = http_url(url)
        if not url:
            raise ScraperError('Informe uma URL http ou https.')
        if is_ad(url):
            raise ScraperError('URL publicitária rejeitada.')
        headers = {'User-Agent': USER_AGENT}
        if referer:
            headers['Referer'] = referer
        if first_bytes:
            headers['Range'] = 'bytes=0-1023'
        if extra_headers:
            headers.update({key: extra_headers[key] for key in PLAYBACK_HEADERS
                            if extra_headers.get(key)})
        host = urlsplit(url).hostname
        LOG.info('Abrindo %s%s', host, ' para verificar a mídia' if first_bytes else '')
        try:
            return self.opener.open(Request(url, headers=headers), timeout=self.timeout)
        except HTTPError as error:
            status = error.code
            host = urlsplit(error.geturl()).hostname or host
            detail = ''
            with error:
                if error.headers.get_content_type() in ('application/xml', 'text/xml'):
                    try:
                        document = ElementTree.fromstring(error.read(4096))
                        code = document.findtext('Code', '').strip()
                        if re.fullmatch(r'[A-Za-z]{1,40}', code):
                            detail = ' ({})'.format(code)
                    except (ElementTree.ParseError, OSError):
                        LOG.debug('Não foi possível ler o código XML da resposta HTTP.')
            category = {401: 'autorização exigida', 403: 'acesso negado',
                        404: 'recurso indisponível', 410: 'recurso indisponível'}.get(status)
            if status == 400 and detail in (' (InvalidArgument)', ' (AuthorizationHeaderMalformed)'):
                category = 'requisição de autorização inválida'
            if 300 <= status < 400:
                category = 'redirecionamento não concluído'
            raise ScraperError('HTTP {} em {}{}{}.'.format(
                status, host, detail, ' — ' + category if category else '')) from None
        except (URLError, OSError) as error:
            reason = getattr(error, 'reason', error)
            raise ScraperError('Falha de rede com {} ({}).'.format(host, type(reason).__name__)) from None

    def page(self, url, referer=''):
        with self.open(url, referer) as response:
            final_url = response.geturl()
            if media_type(response.headers) or (
                    media_url(final_url) and response.headers.get_content_type() == 'application/octet-stream'):
                return Page(final_url, '', media=True)
            try:
                initial = response.read(1024)
                if initial[4:8] == b'ftyp' or initial.lstrip().startswith(b'#EXTM3U'):
                    return Page(final_url, '', media=True)
                content = initial + response.read(4 * 1024 * 1024)
            except (OSError, HTTPException):
                raise ScraperError('Falha de rede ao ler {}.'.format(urlsplit(final_url).hostname)) from None
            encoding = response.headers.get_content_charset() or 'utf-8'
            try:
                return Page(final_url, content.decode(encoding, 'replace'))
            except LookupError:
                return Page(final_url, content.decode('utf-8', 'replace'))

    def verify(self, url, referer='', extra_headers=None, *, identifier='', declared=''):
        check_authorization(url)
        with self.open(url, referer, first_bytes=True, extra_headers=extra_headers) as response:
            final = response.geturl()
            status = response.status
            content_type = response.headers.get_content_type()
            LOG.info('Verificação em %s: HTTP %s (%s).', urlsplit(final).hostname, status, content_type)
            if is_ad(final) or ((identifier or declared) and not is_episode_media(final, identifier, declared)):
                raise ScraperError('HTTP {}: destino da mídia sem vínculo com o episódio.'.format(status))
            if (urlsplit(url)[:2] != urlsplit(final)[:2] and extra_headers
                    and any(extra_headers.get(key) for key in ('Cookie', 'Authorization'))):
                raise ScraperError('HTTP {}: a mídia redirecionou para outro servidor com cabeçalhos privados.'.format(
                    status))
            check_authorization(final)
            try:
                body = response.read(1024)
            except (OSError, HTTPException):
                raise ScraperError('Falha de rede ao ler a mídia (HTTP {}).'.format(status)) from None
            manifest = body.lstrip().startswith(b'#EXTM3U')
            mp4 = body[4:8] in (b'ftyp', b'moov', b'mdat', b'free', b'wide', b'styp')
            if status in (200, 206) and (manifest or mp4):
                return status, content_type
            raise ScraperError('HTTP {} ({}): corpo sem assinatura MP4 ou HLS reconhecida.'.format(
                status, content_type))


def next_page(document, url, search):
    def page_number_and_section(href):
        parts = urlsplit(href)
        if search:
            query = parse_qs(parts.query)
            return query.get('page', ['1'])[0], (parts.netloc, parts.path.rstrip('/'))
        match = re.fullmatch(r'(.*)/page/(\d+)/?', parts.path)
        if match:
            return match[2], (parts.netloc, match[1].rstrip('/'))
        return '1', (parts.netloc, parts.path.rstrip('/'))

    current, section = page_number_and_section(url)
    if not current.isdecimal():
        return False, ''
    candidates = []
    for anchor in document.find_all('a'):
        target = http_url((anchor.attrs.get('href') or '').replace(' ', '%20'), url)
        if target:
            number, target_section = page_number_and_section(target)
            if target_section == section and number.isdecimal() and int(number) > int(current):
                candidates.append((int(number), target))
    if candidates:
        number, target = min(candidates)
        return target, str(number)
    return False, ''


class Hinata:
    def __init__(self, *, timeout=TIMEOUT):
        self.client = Client(timeout)

    def menus_hinata(self):
        try:
            page = self.client.page(base + '/')
            menu = Document(page.text).root.find('div', 'mNav')
            if menu:
                items = []
                for anchor in list(menu.find_all('a'))[1:]:
                    link = http_url(anchor.attrs.get('href'), page.url)
                    if link and anchor.text():
                        items.append((anchor.text(), link))
                return items
        except ScraperError as error:
            LOG.warning('Menu HinataSoul: %s', error)
        return []

    def _listing(self, url, *, episodes=False, search=False):
        if not url:
            return [], False, ''
        try:
            page = self.client.page(http_url(url, base + '/'))
        except ScraperError as error:
            LOG.warning('Lista HinataSoul: %s', error)
            return [], False, ''
        document = Document(page.text).root
        container = document.find('div', 'aniContainer' if episodes or search else 'mainContainer')
        items = []
        if container:
            card_class = 'ultimosEpisodiosHomeItem' if episodes else 'ultimosAnimesHomeItem'
            title_class = 'ultimosEpisodiosHomeItemInfosNum' if episodes else 'ultimosAnimesHomeItemInfosNome'
            for card in container.find_all('div', card_class):
                anchor = card.find('a')
                title = card.find('div', title_class)
                if anchor is None or title is None:
                    continue
                link = http_url(anchor.attrs.get('href'), page.url)
                if not link or not title.text():
                    continue
                img = card.find('img')
                image = http_url(img.attrs.get('data-src') or img.attrs.get('src'), page.url) if img else ''
                items.append((title.text(), link, image))
        following, number = next_page(document, page.url, search)
        return items, following, number

    def menus_abrir(self, url):
        return self._listing(url)

    def episodios(self, url):
        return self._listing(url, episodes=True)

    def pesquisa(self, url=None, pesquisa=None):
        if pesquisa:
            url = base + '/busca?' + urlencode({'busca': pesquisa})
        return self._listing(url, search=True)


def player_sources(document, url, *, selected=False):
    scope = document.find('div', element_id='player')
    frame = document.find('iframe', element_id='content1')
    if scope is None and selected:
        scope = document
    streams = []
    if scope:
        for video in scope.find_all('video'):
            for tag in (video, *video.find_all('source')):
                source = http_url(tag.attrs.get('src'), url)
                if source and not is_ad(source) and source not in streams:
                    streams.append(source)
        if frame is None or not frame.attrs.get('src'):
            frame = next((item for item in scope.find_all('iframe')
                          if item.attrs.get('src')), None)
    embedded = http_url(frame.attrs.get('src'), url) if frame else ''
    return streams, embedded


def meta_content_url(document, url):
    for meta in document.find_all('meta'):
        if meta.attrs.get('itemprop', '').lower() == 'contenturl':
            candidate = http_url(meta.attrs.get('content'), url)
            if candidate and not is_ad(candidate):
                return candidate
    return ''


def player_options(document, page_url):
    box = document.find('div', 'videoBox')
    options = {}
    if box:
        for player in box.find_all('div', 'playerContainer'):
            anchor = player.find('a')
            if anchor:
                url = http_url(anchor.attrs.get('href'), page_url)
                if url and not is_ad(url):
                    options[player.attrs.get('id', '')] = url
    if not options and is_anitube(page_url):
        for index in range(1, 4):
            player = document.find('div', 'video_container', element_id='p{}'.format(index))
            anchor = player.find('a') if player else None
            url = http_url(anchor.attrs.get('href'), page_url) if anchor else ''
            if url and not is_ad(url):
                options[str(index - 1)] = url
    return options


def is_anitube(url):
    return urlsplit(url).hostname in ('anitube.vip', 'www.anitube.vip',
                                     'anitube22.vip', 'www.anitube22.vip')


def kodi_url(stream, referer='', headers=None):
    """Monta os headers do player no formato aceito por URLs de mídia do Kodi."""
    headers = headers or {}
    values = {'User-Agent': headers.get('User-Agent') or USER_AGENT}
    referer = headers.get('Referer') or referer
    if referer:
        values['Referer'] = referer
    if headers.get('Cookie'):
        values['Cookie'] = headers['Cookie']
    if headers.get('Origin'):
        values['Origin'] = headers['Origin']
    if headers.get('Authorization'):
        values['Authorization'] = headers['Authorization']
    return stream + '|' + urlencode(values, quote_via=quote)


def refresh_url(document, url):
    for meta in document.find_all('meta'):
        if meta.attrs.get('http-equiv', '').strip().lower() == 'refresh':
            match = re.search(r';\s*url\s*=\s*(.+)$', meta.attrs.get('content', ''), re.IGNORECASE)
            if match:
                return http_url(match[1].strip().strip('\'"'), url)
    return ''


class Resolver:
    def __init__(self, *, timeout=TIMEOUT, browser=False, seconds=75,
                 visible=False, debug=False):
        self.client = Client(timeout)
        self.browser = browser
        self.seconds = seconds
        self.visible = visible
        self.debug = debug
        self.referer = ''
        self.headers = {}
        self.verification = None

    def _validate(self, stream, referer, identifier, declared, headers=None):
        if not is_episode_media(stream, identifier, declared):
            raise ScraperError('Mídia sem vínculo comprovado com o episódio.')
        if headers is None:
            headers = self.client.playback_headers(stream, referer)
        status = self.client.verify(stream, referer, headers, identifier=identifier, declared=declared)
        self.verification = status
        self.referer = referer
        self.headers = headers
        return stream

    def episode_page(self, url):
        target = http_url(url, base + '/')
        if not target:
            raise ScraperError('Informe uma URL HTTP válida.')
        page = self.client.page(target)
        identifier = episode_id(target)
        if identifier:
            source_host = urlsplit(target).hostname
            final_host = urlsplit(page.url).hostname
            if (episode_id(page.url) != identifier
                    or re.sub(r'^www\.', '', source_host) != re.sub(r'^www\.', '', final_host)):
                raise ScraperError('Redirecionamento para {} não preservou o episódio solicitado.'.format(
                    urlsplit(page.url).hostname))
        return page

    def get_player(self, response, player_id=None, *, offline=False):
        self.referer, self.headers, self.verification = '', {}, None
        document = Document(response.text).root
        heading = document.find('h1', 'epTituloNome') or document.find('title')
        title = heading.text() if heading else ''
        identifier = episode_id(response.url)
        declared = meta_content_url(document, response.url) if identifier else ''
        if declared and is_anitube(response.url):
            # O endereço público do episódio e o arquivo têm identificadores distintos.
            media_id = re.search(r'/(\d+)\.(?:mp4|m3u8)$', urlsplit(declared).path, re.I)
            if media_id:
                identifier = media_id[1]
        options = player_options(document, response.url)
        if offline:
            if options:
                raise ScraperError('O HTML lista players {}. Use o HTML salvo de um player para inspecionar a fonte.'.format(
                    ', '.join(options)))
            streams, embedded = player_sources(document, response.url, selected=True)
            if media_url(embedded):
                streams.append(embedded)
            for stream in streams:
                if ((identifier and is_episode_media(stream, identifier, declared))
                        or (not identifier and media_url(stream) and not is_ad(stream))):
                    self.referer = response.url
                    return {'title': title, 'stream': stream}
            raise ScraperError('Nenhuma fonte de mídia encontrada no HTML salvo.')

        if response.media:
            raise ScraperError('Resposta direta de mídia sem uma página de episódio para comprovar o vínculo.')
        if not options:
            if player_id is not None:
                raise ScraperError('Player {} não encontrado na página.'.format(player_id))
            options = {'direto': response.url}
        requested = (str(player_id),) if player_id is not None else (
            tuple(key for key in PLAYER_ORDER if key in options)
            or tuple(options))
        errors = []
        for option in requested:
            if option not in options:
                raise ScraperError('Player {} indisponível. Opções: {}.'.format(option, ', '.join(options)))
            LOG.info('Tentando player %s.', option)
            try:
                target = options[option]
                if self.browser:
                    media = browser_capture(target, response.url, identifier=identifier, declared=declared,
                                            seconds=self.seconds, visible=self.visible, debug=self.debug)
                    stream = self._validate(media['url'], media.get('referer', ''), identifier,
                                            declared, media['headers'])
                else:
                    initial = response if option == 'direto' else None
                    stream = self._follow(target, response.url, identifier, declared, initial=initial)
                return {'title': title, 'stream': stream}
            except ScraperError as error:
                LOG.info('Player %s: %s', option, error)
                errors.append('Player {}: {}'.format(option, error))
        raise ScraperError(' '.join(errors))

    def _resolve_anitube(self, page, identifier, declared):
        host = (urlsplit(page.url).hostname or '').lower()
        if host not in ('anitube22.vip', 'www.anitube22.vip'):
            return ''
        match = re.search(r"\bvar\s+vid\s*=\s*['\"]([^'\"]+)['\"]", page.text)
        if not match:
            return ''
        video = http_url(match.group(1), page.url)
        if not is_episode_media(video, identifier, declared):
            raise ScraperError('A URL declarada pelo player não corresponde ao episódio.')
        ads_url = 'https://cdn.taboola.com/libtrc/unpkg/tfa.js'
        api_url = 'https://ads.animeyabu.net/adblock2.php'
        if ads_url not in page.text or api_url not in page.text:
            raise ScraperError('O player não apresenta a sequência de autorização esperada.')
        parts = urlsplit(page.url)
        origin = parts.scheme + '://' + parts.netloc
        headers = {'User-Agent': USER_AGENT, 'Origin': origin, 'Referer': origin + '/'}
        try:
            request = Request(ads_url, headers=headers)
            with self.client.opener.open(request, timeout=self.client.timeout) as response:
                ad = response.read(2 * 1024 * 1024 + 1)
                if len(ad) > 2 * 1024 * 1024:
                    raise ScraperError('O script de publicidade excedeu o limite permitido.')
                LOG.info('Script de publicidade: HTTP %s.', response.status)
            form = urlencode({'category': 'client', 'type': 'premium',
                              'ad': ad.decode('utf-8'), 'url': video}).encode('utf-8')
            post_headers = dict(headers, **{'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
            request = Request(api_url, data=form, headers=post_headers)
            with self.client.opener.open(request, timeout=self.client.timeout) as response:
                first = json.loads(response.read(1024 * 1024).decode('utf-8'))
                LOG.info('Autorização, primeira etapa: HTTP %s.', response.status)
            token = first[0]['publicidade']
            if not isinstance(token, str) or not token:
                raise ValueError('token ausente')
            query = urlencode({'token': token, 'url': video})
            request = Request(api_url + '?' + query, headers=headers)
            with self.client.opener.open(request, timeout=self.client.timeout) as response:
                second = json.loads(response.read(1024 * 1024).decode('utf-8'))
                LOG.info('Autorização, segunda etapa: HTTP %s.', response.status)
            suffix = second[0]['publicidade']
            if not isinstance(suffix, str) or not suffix.startswith('?'):
                raise ValueError('autorização ausente')
        except HTTPError as error:
            status = error.code
            error.close()
            raise ScraperError('Autorização respondeu HTTP {}.'.format(status)) from None
        except (URLError, OSError, HTTPException):
            raise ScraperError('Falha de rede ao obter autorização para o player.') from None
        except (ValueError, KeyError, IndexError, TypeError, UnicodeError):
            raise ScraperError('Resposta de autorização inválida para o player.') from None
        signed = video + suffix
        return self._validate(signed, origin + '/', identifier, declared, headers)

    def _follow(self, url, referer, identifier, declared, *, initial=None):
        visited = set()
        for _ in range(5):
            if url in visited:
                break
            visited.add(url)
            if media_url(url):
                return self._validate(url, referer, identifier, declared)
            page = initial or self.client.page(url, referer)
            initial = None
            if page.media:
                return self._validate(page.url, referer, identifier, declared)
            resolved = self._resolve_anitube(page, identifier, declared)
            if resolved:
                return resolved
            document = Document(page.text).root
            streams, embedded = player_sources(document, page.url, selected=True)
            failures = []
            for stream in streams:
                try:
                    return self._validate(stream, page.url, identifier, declared)
                except ScraperError as error:
                    failures.append(str(error))
            url = refresh_url(document, page.url) or embedded
            if not url:
                raise ScraperError(' '.join(failures) or
                                   'Nenhuma mídia ou rota HTTP reconhecida em {}.'.format(urlsplit(page.url).hostname))
            referer = page.url
        raise ScraperError('Redirecionamento do player em loop ou com mais de cinco etapas.')

    def meta_refresh_scraper(self, urlfinal):
        page = self.client.page(urlfinal, base + '/')
        target = refresh_url(Document(page.text).root, page.url)
        return self.client.page(target, page.url).text if target else page.text

    def find_stream(self, url, player_id=None):
        try:
            video = self.get_player(self.episode_page(url), player_id)
            return {'title': video['title'], 'stream': kodi_url(video['stream'], self.referer, self.headers)}
        except ScraperError as error:
            try:
                import xbmcgui
            except ImportError:
                LOG.warning('%s', error)
            else:
                xbmcgui.Dialog().notification('Erro Scraper', str(error), xbmcgui.NOTIFICATION_ERROR)
            return {}


# Chromium observa apenas a aba aberta para a qualidade selecionada.
BROWSER_SCRIPT = r"""
'use strict';
const { chromium } = require('playwright-core');
const config = JSON.parse(process.argv[2]);
const note = (...parts) => { if (config.debug) process.stderr.write(parts.join(' ') + '\n'); };
const errorLine = text => process.stderr.write('Navegador: ' + text + '\n');
const hostname = url => { try { return new URL(url).hostname; } catch { return 'desconhecido'; } };
const sleep = ms => new Promise(ok => setTimeout(ok, ms));
const adPath = new RegExp(config.adPath, 'i');
const decodedPath = url => {
  try { return decodeURIComponent(url.pathname); } catch { return url.pathname; }
};
function isAd(url) {
  const parsed = new URL(url);
  const host = parsed.hostname.replace(/\.$/, '').toLowerCase();
  return adPath.test(decodedPath(parsed)) ||
    config.adDomains.some(domain => host === domain || host.endsWith('.' + domain));
}
function isEpisodeMedia(url) {
  if (isAd(url)) return false;
  const filename = decodedPath(new URL(url)).split('/').pop().toLowerCase();
  return url === config.declared ||
    Boolean(config.id && [config.id + '.mp4', config.id + '.m3u8'].includes(filename));
}
function inPlayer(request, page) {
  try {
    let frame = request.frame();
    if (frame.page() !== page) return false;
    while (frame) {
      const url = frame.url();
      if (/^https?:/.test(url) && isAd(url)) return false;
      frame = frame.parentFrame();
    }
    for (let prior = request.redirectedFrom(); prior; prior = prior.redirectedFrom()) {
      if (isAd(prior.url())) return false;
    }
    return true;
  } catch {
    return false;
  }
}
function mediaLike(request, type) {
  const url = new URL(request.url());
  return request.resourceType() === 'media' || /^(video\/|.*mpegurl)/i.test(type) ||
    /\.(mp4|m3u8)$/i.test(url.pathname) ||
    /(?:^|\.)r2\.cloudflarestorage\.com$/i.test(url.hostname) ||
    request.url() === config.declared;
}
(async () => {
  let browser;
  const seen = new Set();
  let found;
  try {
    browser = await chromium.launch({
      executablePath: process.env.CHROMIUM_PATH,
      headless: !config.visible,
      args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
             '--autoplay-policy=no-user-gesture-required', '--no-first-run']
    });
    const context = await browser.newContext({
      userAgent: config.userAgent, locale: 'pt-BR', viewport: {width: 1280, height: 800},
      serviceWorkers: 'block'
    });
    const page = await context.newPage();
    page.on('framenavigated', frame => {
      if (/^https?:/.test(frame.url())) note('Frame do player:', hostname(frame.url()));
    });
    page.on('requestfailed', request => {
      if (mediaLike(request, '')) {
        seen.add('falha de rede em ' + hostname(request.url()));
        note('Falha de rede na mídia:', hostname(request.url()), request.failure()?.errorText || '');
      }
    });
    page.on('response', async response => {
      if (found) return;
      const request = response.request();
      const url = response.url();
      const status = response.status();
      const type = (response.headers()['content-type'] || '').split(';')[0].trim().toLowerCase();
      if (!mediaLike(request, type)) {
        if (request.isNavigationRequest()) note('Navegação:', hostname(url), 'HTTP', status);
        return;
      }
      const host = hostname(url);
      const parsed = new URL(url);
      const r2 = /(?:^|\.)r2\.cloudflarestorage\.com\.?$/i.test(parsed.hostname);
      const signed = Array.from(parsed.searchParams.entries()).some(
        ([key, value]) => key.toLowerCase() === 'x-amz-signature' && value);
      const reason = isAd(url) ? 'publicidade rejeitada' :
        !inPlayer(request, page) ? 'fora do iframe ou da aba selecionada' :
        r2 && !signed ? 'R2 sem assinatura' :
        !isEpisodeMedia(url) ? 'sem vínculo com o episódio' :
        ![200, 206].includes(status) ? 'mídia indisponível ou acesso negado' :
        /^(text\/html|application\/(json|xml)|text\/xml)$/.test(type) ? 'corpo não é mídia' : '';
      const safeType = /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/.test(type) ? type : '';
      note('Mídia:', host, 'HTTP', status, safeType, signed ? 'assinada' : '', reason);
      if (reason) {
        seen.add(host + ' HTTP ' + status + ' (' + reason + ')');
        return;
      }
      try {
        const requestHeaders = await request.allHeaders();
        if (found) return;
        const headers = {};
        for (const key of config.headers) {
          const value = requestHeaders[key.toLowerCase()];
          if (value) headers[key] = value;
        }
        found = {url, status, content_type: safeType, referer: headers.Referer || '', headers};
      } catch {
        seen.add('cabeçalhos de mídia indisponíveis em ' + host);
      }
    });
    const deadline = Date.now() + config.seconds * 1000;
    try {
      const navigation = await page.goto(config.target, {
        waitUntil:'domcontentloaded', timeout: Math.min(config.seconds * 1000, 25000),
        referer: config.referer || undefined
      });
      if (navigation && navigation.status() >= 400) {
        seen.add('player HTTP ' + navigation.status() + ' em ' + hostname(navigation.url()));
      }
    } catch (error) {
      note('Falha na navegação inicial:', error.name === 'TimeoutError' ? 'tempo excedido' : 'rede ou redirecionamento');
    }
    const clicked = new Set();
    while (!found && !page.isClosed() && Date.now() < deadline) {
      for (const frame of page.frames()) {
        if (found || Date.now() >= deadline) break;
        if (!/^https?:/.test(frame.url()) || isAd(frame.url())) continue;
        try {
          await frame.evaluate(() => {
            for (const video of document.querySelectorAll('video')) {
              if (video.paused && (video.currentSrc || video.src || video.querySelector('source'))) {
                video.play().catch(() => {});
              }
            }
          });
          const key = frame.url();
          if (clicked.has(key)) continue;
          const button = frame.locator(
            '.jw-display-icon-container, .vjs-big-play-button, .plyr__control--overlaid, button[aria-label="Play Video"], button[aria-label="Play"]'
          ).first();
          if (await button.isVisible()) {
            clicked.add(key);
            await button.click({timeout: 900});
          }
        } catch {
          note('Frame mudou ou controle indisponível em', hostname(frame.url()));
        }
      }
      if (!found) await sleep(400);
    }
    if (found) {
      process.stdout.write(JSON.stringify(found) + '\n');
    } else {
      errorLine('nenhuma mídia confirmada para o episódio.' +
        (seen.size ? ' ' + Array.from(seen).slice(0, 8).join('; ') + '.' : ''));
      process.exitCode = 2;
    }
  } catch (error) {
    errorLine('falha ao executar o Chromium (' + (error.name === 'TimeoutError' ? 'tempo excedido' : 'inicialização ou sessão') + ').');
    process.exitCode = 2;
  } finally {
    if (browser) await browser.close().catch(() => {});
  }
})();
"""


def browser_capture(target, referer, *, identifier='', declared='', seconds=75,
                    visible=False, debug=False):
    node = shutil.which('node')
    chromium_path = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium-browser') or shutil.which('chromium')
    if not node or not chromium_path:
        raise ScraperError('Modo navegador exige Node.js, Chromium e playwright-core.')
    env = os.environ.copy()
    env['CHROMIUM_PATH'] = chromium_path
    env.setdefault('PLAYWRIGHT_BROWSERS_PATH', '0')
    modules = [str(Path.home() / '.aniplay-runtime' / 'node_modules'),
               str(Path(__file__).resolve().parent / 'node_modules')]
    if env.get('NODE_PATH'):
        modules.append(env['NODE_PATH'])
    env['NODE_PATH'] = os.pathsep.join(modules)
    config = dict(target=target, referer=referer, id=identifier or episode_id(referer),
                  declared=declared, seconds=seconds, visible=visible, debug=debug,
                  userAgent=USER_AGENT, adPath=AD_PATH, adDomains=AD_DOMAINS, headers=PLAYBACK_HEADERS)
    try:
        result = subprocess.run([node, '-', json.dumps(config)], input=BROWSER_SCRIPT,
                                capture_output=True, text=True, env=env, timeout=seconds + 30)
    except subprocess.TimeoutExpired:
        raise ScraperError('O Chromium excedeu o tempo limite da captura.') from None
    except OSError:
        raise ScraperError('Não foi possível executar o Node.js.') from None
    if debug:
        for line in result.stderr.splitlines():
            if line.startswith(('Frame do player:', 'Falha de rede na mídia:', 'Navegação:',
                                'Mídia:', 'Falha na navegação inicial:', 'Frame mudou')):
                LOG.info('%s', line)
    if result.returncode:
        if 'Cannot find module' in result.stderr and 'playwright-core' in result.stderr:
            raise ScraperError('Instale playwright-core com npm install --prefix ~/.aniplay-runtime playwright-core.')
        detail = next((line for line in reversed(result.stderr.splitlines())
                       if line.startswith('Navegador: ')), 'O processo do Chromium falhou.')
        raise ScraperError(detail)
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise ScraperError('Resposta inválida do Chromium.') from None
    if not is_episode_media(data.get('url', ''), config['id'], declared):
        raise ScraperError('O Chromium retornou uma URL sem vínculo com o episódio.')
    LOG.info('Chromium recebeu HTTP %s (%s).', data['status'], data['content_type'])
    return data


def select_player_url(document, page_url, player_id):
    options = player_options(document, page_url)
    if not options:
        return None
    if player_id is not None:
        key = str(player_id)
        if key not in options:
            raise ScraperError('Player {} não encontrado. Opções: {}'.format(key, ', '.join(options)))
        return options[key]
    return next((options[key] for key in PLAYER_ORDER if key in options), next(iter(options.values())))


def main():
    parser = argparse.ArgumentParser(description='Extrai a URL de vídeo de um episódio ou um HTML salvo.')
    parser.add_argument('url', nargs='?', help='URL do episódio do HinataSoul')
    parser.add_argument('--html', type=Path, help='Analisa um HTML local')
    quality = parser.add_mutually_exclusive_group()
    quality.add_argument('--auto', action='store_true', help='Tenta Full HD, HD e SD (padrão)')
    quality.add_argument('--player', choices=('0', '1', '2'), help='Escolhe uma opção específica do HinataSoul')
    parser.add_argument('--verificar', action='store_true', help='Solicita o início da mídia para verificar a resposta')
    parser.add_argument('--debug', action='store_true', help='Mostra as etapas da extração')
    parser.add_argument('--navegador', action='store_true', help='Usa Chromium para obter a requisição de mídia autorizada')
    parser.add_argument('--janela', action='store_true', help='Mostra a janela do Chromium (requer Termux:X11 ou ambiente gráfico)')
    parser.add_argument('--tempo', type=int, default=75, help='Tempo máximo da captura pelo navegador (padrão: 75 s)')
    parser.add_argument('--meta', action='store_true', help='Testa a URL alternativa de contentURL publicada no HTML')
    parser.add_argument('--kodi', action='store_true', help='Devolve URL com cabeçalhos do Kodi (pode conter cookie de sessão)')
    parser.add_argument('--timeout-http', type=float, default=TIMEOUT, help='Timeout HTTP em segundos')
    parser.add_argument('--url-base', help='URL original do HTML salvo para resolver links relativos')
    args = parser.parse_args()
    if bool(args.url) == bool(args.html):
        parser.error('Informe a URL do episódio ou use --html ARQUIVO.')

    if args.tempo <= 0 or not 0 < args.timeout_http < float('inf'):
        parser.error('Os tempos devem ser positivos e finitos.')
    if args.navegador and (args.html or args.meta):
        parser.error('--navegador exige uma URL de episódio e seleção de player.')
    if args.url_base and (not args.html or not http_url(args.url_base)):
        parser.error('--url-base exige --html e uma URL HTTP válida.')
    if args.debug:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
    resolver = Resolver(timeout=args.timeout_http, browser=args.navegador,
                        seconds=args.tempo, visible=args.janela, debug=args.debug)
    try:
        if args.html:
            page = Page(args.url_base or '', args.html.read_text(encoding='utf-8-sig', errors='replace'))
        else:
            page = resolver.episode_page(args.url)
        if args.meta:
            declared = meta_content_url(Document(page.text).root, page.url)
            if not declared:
                raise ScraperError('Não encontrei contentURL de mídia no HTML.')
            if not args.html or args.verificar:
                resolver._validate(declared, page.url, episode_id(page.url), declared)
            stream = declared
        else:
            stream = resolver.get_player(page, args.player, offline=bool(args.html))['stream']
        if args.verificar:
            status, content_type = resolver.verification or resolver.client.verify(
                stream, resolver.referer, identifier=episode_id(page.url),
                declared=meta_content_url(Document(page.text).root, page.url))
            print('Mídia respondeu HTTP {} ({}).'.format(status, content_type), file=sys.stderr)
        print(kodi_url(stream, resolver.referer, resolver.headers) if args.kodi else stream, flush=True)
    except (ScraperError, OSError, ValueError) as error:
        message = str(error) if isinstance(error, ScraperError) else type(error).__name__
        print('Erro: {}'.format(message), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
