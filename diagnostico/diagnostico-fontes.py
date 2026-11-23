"""Teste de conectividade das fontes do AniPlay. Requer apenas Python 3."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


FONTES = (
    ('Bakashi', 'https://bakashi.top/lista-de-animes', 'search'),
    ('HinataSoul', 'https://www.hinatasoul.com/busca', 'busca'),
    ('AniTube22', 'https://www.anitube22.vip/busca', 's'),
    ('AniTube', 'https://anitube.vip/busca', 's'),
    ('AniTube com www', 'https://www.anitube.vip/busca', 's'),
)
CLIENTES = (
    ('Kodi', 'Mozilla/5.0 (Kodi; AniPlay)'),
    ('Scraper', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0'),
)


def testar(job):
    (fonte, base, param), (cliente, ua) = job
    url = base + '?' + urlencode({param: 'One Piece'})
    inicio = monotonic()
    try:
        request = Request(url, headers={'User-Agent': ua, 'Accept': '*/*'})
        with build_opener(SemRedirecionamento()).open(request, timeout=8) as resposta:
            detalhe = f'HTTP={resposta.status} tipo={resposta.headers.get_content_type()}'
    except HTTPError as erro:
        destino = urlsplit(urljoin(url, erro.headers.get('Location', ''))) if erro.headers.get('Location') else None
        detalhe = f'HTTP={erro.code}'
        if destino:
            detalhe += f' destino={destino.scheme}://{destino.hostname}'
        erro.close()
    except OSError as erro:
        causa = erro.reason if isinstance(erro, URLError) else erro
        detalhe = f'erro={type(causa).__name__}'
    return f'{fonte} | cliente={cliente} | {detalhe} | ms={round((monotonic() - inicio) * 1000)}'


if __name__ == '__main__':
    print('UTC', datetime.now(timezone.utc).isoformat(timespec='seconds'))
    print('Busca de teste: One Piece. Examina a primeira resposta HTTP, sem seguir redirecionamentos.')
    jobs = [(fonte, cliente) for fonte in FONTES for cliente in CLIENTES]
    with ThreadPoolExecutor(max_workers=5) as pool:
        for linha in pool.map(testar, jobs):
            print(linha)
