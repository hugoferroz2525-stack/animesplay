"""Catálogo experimental com fontes independentes."""
from aniplay.providers.scraper import Document, http_url, next_page

FONTES = (
    ('HinataSoul', 'https://www.hinatasoul.com', 'hinata'),
    ('AniTube22', 'https://www.anitube22.vip', 'anitube'),
    ('AniTube', 'https://www.anitube.vip', 'anitube'),
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
        link, img = card.find('a'), card.find('img')
        titulo = next((node for tag in ('div', 'span', 'a') if (node := card.find(tag, titulo_classe))), None)
        if not link or not titulo:
            continue
        target = http_url(link.attrs.get('href'), url)
        imagem = http_url(img.attrs.get('data-src') or img.attrs.get('src'), url) if img else ''
        if target and titulo.text():
            episodios.append((titulo.text(), target, imagem))
    proxima, numero = next_page(documento, url)
    return episodios, proxima, numero


