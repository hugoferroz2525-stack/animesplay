"""Políticas de origem para o catálogo, TMDB e servidores de mídia."""
import ipaddress
import socket
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

CATALOG_HOST = 'bakashi.top'
PROVIDER_HOSTS = ('www.hinatasoul.com', 'www.anitube22.vip', 'anitube.vip', 'www.anitube.vip')
TMDB_HOST = 'api.themoviedb.org'
CLOUD_HOST = 'aniplay-experimental.aniplay-lab-2525.workers.dev'


def validate_url(url, host=None):
    parts = urlsplit(url)
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username is not None or parts.password is not None
            or '\\' in url or any(ord(char) <= 32 or ord(char) == 127 for char in url)):
        raise ValueError('Endereço de rede inválido.')
    port = parts.port
    if port is None:
        port = 443 if parts.scheme == 'https' else 80
    if host:
        if parts.scheme != 'https' or parts.hostname != host or port != 443:
            raise ValueError('Endereço fora da origem permitida.')
        return
    addresses = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    for *_, sockaddr in addresses:
        address = ipaddress.ip_address(sockaddr[0].split('%', 1)[0])
        address = getattr(address, 'ipv4_mapped', None) or address
        if not address.is_global or address.is_multicast:
            raise ValueError('O servidor de mídia precisa ter um endereço público.')


class RedirectRejected(ValueError):
    def __init__(self, status, destination):
        super().__init__('Redirecionamento fora da origem permitida.')
        parts = urlsplit(destination)
        self.status = status
        self.destination = f'{parts.scheme}://{parts.hostname or "?"}'


class CheckedRedirect(HTTPRedirectHandler):
    def __init__(self, host):
        self.host = host

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            validate_url(newurl, self.host)
        except (OSError, ValueError) as error:
            raise RedirectRejected(code, newurl) from error
        redirect = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirect and urlsplit(req.full_url).netloc != urlsplit(newurl).netloc:
            for header in ('Authorization', 'Cookie', 'Api-key'):
                redirect.remove_header(header)
        return redirect


class CheckedOpener:
    def __init__(self, host=None):
        self.host = host
        self.opener = build_opener(CheckedRedirect(host))

    def open(self, request, timeout):
        validate_url(request.full_url, self.host)
        return self.opener.open(request, timeout=timeout)


media_opener = CheckedOpener()
