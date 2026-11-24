import json
from math import isfinite
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def markers(payload, duration):
    matches = {'op': set(), 'ed': set()}
    if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
        return []
    for result in payload['results']:
        try:
            kind = result['skipType']
            if kind not in matches:
                continue
            start = float(result['interval']['startTime'])
            end = float(result['interval']['endTime'])
            length = float(result['episodeLength'])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if (all(isfinite(value) for value in (start, end, length, duration))
                and abs(length - duration) <= 2
                and 0 <= start < end <= duration and 3 <= end - start <= 180):
            matches[kind].add((start, end))
    intervals = [(kind, *next(iter(marker))) for kind, marker in matches.items() if len(marker) == 1]
    if len(intervals) == 2 and intervals[0][1] < intervals[1][2] and intervals[1][1] < intervals[0][2]:
        return []
    return intervals


def lookup(mal, episode, duration):
    query = urlencode({'types': ('op', 'ed'), 'episodeLength': round(duration, 3)}, doseq=True)
    url = 'https://api.aniskip.com/v2/skip-times/{}/{}?{}'.format(int(mal), int(episode), query)
    with urlopen(Request(url,headers={'Accept':'application/json','User-Agent':'AniPlay (Kodi)'}), timeout=3) as response:
        payload = json.loads(response.read(65537))
    return markers(payload, duration)
