"""Agrupamento conservador de fontes de animes."""
import re
import unicodedata
from dataclasses import dataclass, field


def chave_titulo(titulo):
    texto = unicodedata.normalize('NFKD', titulo.casefold())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r'\b(dublado|dublada|dub)\b', ' dublado ', texto)
    texto = re.sub(r'\b(legendado|legendada|sub)\b', ' legendado ', texto)
    return re.sub(r'\s+', ' ', re.sub(r'[^\w]+', ' ', texto)).strip()


@dataclass
class AnimeAgrupado:
    titulo: str
    fontes: list = field(default_factory=list)


def agrupar_animes(resultados):
    """Recebe (site, título, URL, imagem) e retorna grupos com fontes únicas."""
    grupos = {}
    for site, titulo, url, imagem in resultados:
        chave = chave_titulo(titulo)
        if not chave or not url:
            continue
        grupo = grupos.setdefault(chave, AnimeAgrupado(titulo))
        if not any(item['site'] == site and item['url'] == url for item in grupo.fontes):
            grupo.fontes.append({'site': site, 'url': url, 'imagem': imagem})
    return list(grupos.values())
