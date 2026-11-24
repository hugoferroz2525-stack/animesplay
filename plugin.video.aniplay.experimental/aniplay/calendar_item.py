from functools import lru_cache
from aniplay.data_files import load as load_data
from urllib.parse import urlencode

from source import BASE
from aniplay.menu_metadata import catalog
from aniplay.tmdb_match import index, normalized
from aniplay.views import item, yellow


@lru_cache(maxsize=1)
def mal_records():
    mal_ids=load_data('aniskip-ids.json')
    records,_=catalog()
    matches={}
    for key,(kind,ident,season) in index().items():
        if key not in records or kind!='tv':
            continue
        mal=mal_ids.get(f'{ident}/{season if season is not None else 1}')
        if mal:
            matches.setdefault(str(mal),[]).append(records[key])
    return matches


def add(when,title,number,entry):
    _,names=catalog()
    alternatives=[entry.get(k) for k in ('title','title_romaji','title_japanese')]
    record=next((names[normalized(n)] for n in alternatives if n and names.get(normalized(n))),None)
    if not record:
        candidates=mal_records().get(str(entry.get('mal_id')),[])
        if len(candidates)==1:
            record=candidates[0]
    label = f"{yellow(when.strftime('%H:%M'))} · {title}"
    if number is not None:
        label += f' · EP {number}'
    if record:
        item(label,'show',dict(url=record[1]),art=record[2] or entry.get('image',''))
        return
    term=entry.get('title_romaji') or title
    plot=' · '.join(str(v) for v in [entry.get('format'),entry.get('status'),*(entry.get('genres') or [])] if v)
    item(label,'catalog',dict(url=BASE+'/lista-de-animes?'+urlencode({'search':term})),
         data={},art=entry.get('image',''),icon='clock',info=dict(plot=plot+'\nBuscar no catálogo por '+term+'.'))
