"""Catálogo experimental com fontes independentes."""
from urllib.parse import urlencode, urlsplit
from scraper import Client, Document, ScraperError, http_url, next_page
from agrupamento_animes import agrupar_animes

FONTES = (
    ('HinataSoul', 'https://www.hinatasoul.com', 'hinata'),
    ('AniTube22', 'https://www.anitube22.vip', 'anitube'),
    ('AniTube', 'https://anitube.vip', 'anitube'),
)


def extrair_animes(html, url, tipo):
    documento = Document(html).root
    resultados = []
    if tipo == 'hinata':
        cards = documento.find_all('div', 'ultimosAnimesHomeItem')
        for card in cards:
            anchor = card.find('a')
            title = card.find('div', 'ultimosAnimesHomeItemInfosNome')
            img = card.find('img')
            if anchor and title:
                nome = (img.attrs.get('title') or img.attrs.get('alt') or title.text()) if img else title.text()
                link = http_url(anchor.attrs.get('href'), url)
                imagem = http_url(img.attrs.get('data-src') or img.attrs.get('src'), url) if img else ''
                if nome and link:
                    resultados.append((nome, link, imagem))
    elif tipo == 'anitube':
        for card in documento.find_all('div', 'ani_loop_item'):
            title = card.find('a', 'ani_loop_item_infos_nome')
            img = card.find('img')
            if title:
                nome = (img.attrs.get('title') or img.attrs.get('alt') or title.text()) if img else title.text()
                link = http_url(title.attrs.get('href'), url)
                imagem = http_url(img.attrs.get('data-src') or img.attrs.get('src'), url) if img else ''
                if nome and link:
                    resultados.append((nome, link, imagem))
    return resultados


def pesquisar(termo=None, timeout=15):
    """Consulta novamente cada fonte em toda pesquisa; devolve grupos e erros."""
    resultados, erros = [], {}
    for site, base, tipo in FONTES:
        parametro = 'busca' if tipo == 'hinata' else 's'
        url = base + '/busca?' + urlencode({parametro: termo}) if termo else base + '/'
        client = Client(timeout)
        visitadas = set()
        try:
            while url and url not in visitadas:
                visitadas.add(url)
                page = client.page(url)
                esperado = (urlsplit(base).hostname or '').removeprefix('www.')
                destino = (urlsplit(page.url).hostname or '').removeprefix('www.')
                if destino != esperado:
                    raise ScraperError('redirecionado para outro domínio')
                encontrados = extrair_animes(page.text, page.url, tipo)
                resultados.extend((site, titulo, link, imagem) for titulo, link, imagem in encontrados)
                url = next_page(Document(page.text).root, page.url, True)[0] if termo else ''
        except ScraperError as erro:
            erros[site] = str(erro)
    return agrupar_animes(resultados), erros


def extrair_episodios(html, url, tipo):
    """Extrai episódios da página atual e informa o link da próxima página."""
    documento = Document(html).root
    if tipo == 'anitube':
        classe, titulo_classe = 'animepag_episodios_item', 'animepag_episodios_item_nome'
    elif tipo == 'hinata':
        classe, titulo_classe = 'ultimosEpisodiosHomeItem', 'ultimosEpisodiosHomeItemInfosNum'
    else:
        raise ValueError('Fonte não reconhecida.')
    episodios = []
    for card in documento.find_all('div', classe):
        link, titulo, img = card.find('a'), card.find('div', titulo_classe), card.find('img')
        if not link or not titulo:
            continue
        target = http_url(link.attrs.get('href'), url)
        imagem = http_url(img.attrs.get('data-src') or img.attrs.get('src'), url) if img else ''
        if target and titulo.text():
            episodios.append((titulo.text(), target, imagem))
    proxima, numero = next_page(documento, url, False)
    return episodios, proxima, numero


def listar_episodios(fontes, timeout=8):
    """Agrupa somente números explícitos; itens sem número mantêm identidade própria."""
    import re
    grupos, erros = {}, {}
    tipos = {nome: tipo for nome, _, tipo in FONTES}
    for fonte in fontes:
        site, url = fonte['site'], fonte['url']
        client = Client(timeout)
        visitadas = set()
        try:
            while url and url not in visitadas:
                visitadas.add(url)
                page = client.page(url)
                if (urlsplit(url).hostname or '').removeprefix('www.') != (
                        urlsplit(page.url).hostname or '').removeprefix('www.'):
                    raise ScraperError('redirecionado para outro domínio')
                itens, url, _ = extrair_episodios(page.text, page.url, tipos[site])
                for titulo, link, _ in itens:
                    match = re.search(r'\b(?:ep\.?|epis[oó]dio)\s*(\d+)\s*$', titulo, re.I)
                    chave = (0, int(match[1])) if match else (1, link)
                    grupo = grupos.setdefault(chave, {'titulo': titulo, 'fontes': []})
                    servidor = {'site': site, 'url': link}
                    if servidor not in grupo['fontes']:
                        grupo['fontes'].append(servidor)
        except ScraperError as erro:
            erros[site] = str(erro)
    return [grupos[chave] for chave in sorted(grupos)], erros


def resolver_servidores(fontes, timeout=12, player_id=None):
    from scraper import Resolver, kodi_url
    for fonte in fontes:
        resolver = Resolver(timeout=timeout)
        try:
            video = resolver.get_player(resolver.episode_page(fonte['url']), player_id)
        except ScraperError:
            continue
        return video['title'], kodi_url(video['stream'], resolver.referer, resolver.headers)
    return None


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Busca e agrupa animes das fontes disponíveis.')
    parser.add_argument('titulo', nargs='?', help='Sem título, consulta as páginas iniciais.')
    args = parser.parse_args()
    grupos, erros = pesquisar(args.titulo)
    for grupo in grupos:
        print(grupo.titulo)
        for numero, fonte in enumerate(grupo.fontes, 1):
            print('  Servidor {} · {}'.format(numero, fonte['site']))
    for site, erro in erros.items():
        print('{}: {}'.format(site, erro), file=sys.stderr)
