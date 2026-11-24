from datetime import datetime

HOME = [
    ('Continuar assistindo','continue','resume','Retome os episódios que você interrompeu.'),
    ('Assistidos','watched','watched','Reveja os episódios que você concluiu.'),
    ('Minha lista','favorites','favorites','Abra os animes que você salvou pelo menu de contexto.'),
    ('Histórico de reprodução','recent','history','Volte aos últimos episódios que começaram a tocar.'),
    ('Lançamentos','latest','latest','Veja os episódios publicados recentemente pelo Bakashi.'),
    ('Catálogo de animes','catalog','all','Explore as obras e escolha o servidor de cada anime.'),
    ('Em alta no Bakashi','trending','trending','Animações japonesas disponíveis no Bakashi por popularidade no TMDB.'),
    ('Explorar por filtro','filters','filters','Escolha gênero, formato, ano ou situação de lançamento.'),
    ('Buscar e ver histórico','search','search','Procure um anime pelo nome ou repita uma busca anterior.'),
    ('Calendário de lançamentos','calendar','calendar','Consulte a programação por dia no horário do seu dispositivo.'),
    ('Configurações','settings','settings','Configure metadados, áudio, botão de abertura, biblioteca e cache.'),
]
DAYS = ('Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira','Sexta-feira','Sábado','Domingo')


def schedule(days):
    grouped = {}
    for entries in days.values():
        for entry in entries or []:
            if not isinstance(entry, dict) or not isinstance(entry.get('title'), str) or not entry['title'].strip():
                continue
            try:
                when = datetime.fromtimestamp(entry['airing_at'])
            except (KeyError, TypeError, ValueError, OverflowError, OSError):
                continue
            episode = entry.get('episode')
            if not isinstance(episode, (int, float, str)):
                episode = None
            key = (when, entry['title'], str(episode) if episode is not None else '')
            grouped.setdefault(when.date(), {})[key] = entry
    return grouped
