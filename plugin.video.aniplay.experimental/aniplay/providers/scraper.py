# -*- coding: utf-8 -*-
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from html.parser import HTMLParser
from http.client import HTTPException
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

from aniplay.network import validate_url


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


class NoPlayerMedia(ScraperError):
    """O HTML abriu sem mídia ou rota de player reconhecível."""


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
        try:
            validate_url(newurl)
        except (OSError, ValueError):
            raise ScraperError('Redirecionamento para um endereço indisponível.') from None
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
        self.dimension_prefix = None

    def playback_headers(self, url, referer):
        request = Request(url)
        self.cookies.add_cookie_header(request)
        headers = {'User-Agent': USER_AGENT}
        if referer:
            headers['Referer'] = referer
        if request.has_header('Cookie'):
            headers['Cookie'] = request.get_header('Cookie')
        return headers

    def open(self, url, referer='', first_bytes=False, extra_headers=None, byte_range=None):
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
        if byte_range is not None:
            start, length = byte_range
            headers['Range'] = f'bytes={start}-{start + length - 1}'
        if extra_headers:
            headers.update({key: extra_headers[key] for key in PLAYBACK_HEADERS
                            if extra_headers.get(key)})
        host = urlsplit(url).hostname
        LOG.info('Abrindo %s%s', host, ' para verificar a mídia' if first_bytes else '')
        try:
            validate_url(url)
            return self.opener.open(Request(url, headers=headers), timeout=self.timeout)
        except ValueError:
            raise ScraperError('Endereço indisponível.') from None
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
        sample_size = 131072 if self.dimension_prefix is not None else 1024
        byte_range = (0, sample_size) if self.dimension_prefix is not None else None
        with self.open(url, referer, first_bytes=True, extra_headers=extra_headers, byte_range=byte_range) as response:
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
                body = response.read(sample_size)
            except (OSError, HTTPException):
                raise ScraperError('Falha de rede ao ler a mídia (HTTP {}).'.format(status)) from None
            manifest = body.lstrip().startswith(b'#EXTM3U')
            mp4 = body[4:8] in (b'ftyp', b'moov', b'mdat', b'free', b'wide', b'styp')
            if status in (200, 206) and (manifest or mp4):
                if self.dimension_prefix is not None:
                    self.dimension_prefix = body
                return status, content_type
            raise ScraperError('HTTP {} ({}): corpo sem assinatura MP4 ou HLS reconhecida.'.format(
                status, content_type))


def next_page(document, url):
    def page_number_and_section(href):
        parts = urlsplit(href)
        query = parse_qs(parts.query)
        number = next((query.pop(key)[0] for key in ('page', 'paged', 'pagina') if key in query), '1')
        path = parts.path.rstrip('/')
        match = re.fullmatch(r'(.*)/page/(\d+)', path)
        if match:
            path, number = match.groups()
        scope = (parts.netloc, path, tuple(sorted((key, tuple(values)) for key, values in query.items())))
        return number, scope


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


def refresh_url(document, url):
    for meta in document.find_all('meta'):
        if meta.attrs.get('http-equiv', '').strip().lower() == 'refresh':
            match = re.search(r';\s*url\s*=\s*(.+)$', meta.attrs.get('content', ''), re.IGNORECASE)
            if match:
                return http_url(match[1].strip().strip('\'"'), url)
    return ''


class Resolver:
    def __init__(self, *, timeout=TIMEOUT):
        self.client = Client(timeout)
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
        episode_origin = urlsplit(response.url)
        hinata_episode = (episode_origin.scheme == 'https'
                          and episode_origin.hostname == 'www.hinatasoul.com'
                          and urlsplit(declared).scheme == 'https')
        if declared and (is_anitube(response.url) or hinata_episode):
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
        missing_media = []
        for option in requested:
            if option not in options:
                raise ScraperError('Player {} indisponível. Opções: {}.'.format(option, ', '.join(options)))
            LOG.info('Tentando player %s.', option)
            try:
                target = options[option]
                initial = response if option == 'direto' else None
                stream = self._follow(target, response.url, identifier, declared, initial=initial)
                return {'title': title, 'stream': stream}
            except ScraperError as error:
                LOG.info('Player %s: %s', option, error)
                errors.append('Player {}: {}'.format(option, error))
                missing_media.append(isinstance(error, NoPlayerMedia))
        failure = NoPlayerMedia if missing_media and all(missing_media) else ScraperError
        raise failure(' '.join(errors))

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
                if failures:
                    raise ScraperError(' '.join(failures))
                raise NoPlayerMedia('Nenhuma mídia ou rota HTTP reconhecida em {}.'.format(urlsplit(page.url).hostname))
            referer = page.url
        raise ScraperError('Redirecionamento do player em loop ou com mais de cinco etapas.')



def quality_label(value):
    value = re.sub(r'[_-]+', ' ', value).upper()
    height = re.search(r'\b(240|360|480|540|720|1080|1440|2160)P?\b', value)
    if height:
        return height[1] + 'p'
    if re.search(r'\b(?:FULL\s*HD|FHD)\b', value):
        return '1080p'
    if re.search(r'\b(?:ULTRA\s*HD|UHD|4K)\b', value):
        return '2160p'
    if re.search(r'\bHD\b', value):
        return '720p'
    if re.search(r'\bSD\b', value):
        return 'SD'
    return ''


def mp4_height(resolver, stream):
    """Read track dimensions using bounded ranges, skipping the media payload."""
    offset = 0
    limit = 131072
    prefix = resolver.client.dimension_prefix
    for _ in range(8):
        if offset == 0 and prefix:
            data = prefix
        else:
            with resolver.client.open(stream, resolver.referer, extra_headers=resolver.headers,
                                      byte_range=(offset, limit)) as response:
                if offset and (response.status != 206 or not response.headers.get(
                        'Content-Range', '').startswith(f'bytes {offset}-')):
                    return None
                data = response.read(limit)
        pos = 0
        while pos + 8 <= len(data):
            size = int.from_bytes(data[pos:pos+4], 'big')
            kind = data[pos+4:pos+8]
            header = 8
            if size == 1:
                header = 16
                size = int.from_bytes(data[pos+8:pos+16], 'big')
            if size < header:
                return None
            if kind in (b'moov', b'trak'):
                pos += header
                continue
            if kind == b'tkhd' and pos + size <= len(data) and size >= 84:
                width = int.from_bytes(data[pos+size-8:pos+size-4], 'big') >> 16
                height = int.from_bytes(data[pos+size-4:pos+size], 'big') >> 16
                if width and 1 <= height <= 8640:
                    return height
            pos += size
        if not pos or len(data) < limit and pos <= len(data):
            return None
        offset += pos
    return None


def quality_choices(response):
    document = Document(response.text).root
    options = player_options(document, response.url)
    scope = document.find('div', element_id='player') or document
    choices = []
    for video in scope.find_all('video'):
        for tag in (video, *video.find_all('source')):
            label = quality_label(' '.join(tag.attrs.get(key, '')
                                  for key in ('label', 'res', 'data-quality', 'title')))
            stream = http_url(tag.attrs.get('src'), response.url)
            if label and stream and not is_ad(stream):
                choices.append((label, 'source', stream))
    for j, (player, url) in enumerate(options.items(), 1):
        anchor = next((tag for tag in document.find_all('a')
                       if http_url(tag.attrs.get('href'), response.url) == url), None)
        text = ' '.join((anchor.text(), anchor.attrs.get('title', ''), anchor.attrs.get('data-quality', ''))) if anchor else ''
        choices.append((quality_label(text) or f'Player {j}', 'player', player))
    return list(dict.fromkeys(choices))
