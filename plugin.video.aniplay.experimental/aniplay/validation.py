from aniplay.streams.validation import probe
from aniplay.network import media_opener
from source import UA


def probe_media(url, referer):
    headers = {'Referer': referer, 'User-Agent': UA, 'Accept': '*/*'}
    return probe({'url': url, 'headers': headers}, opener=media_opener)['mime']
