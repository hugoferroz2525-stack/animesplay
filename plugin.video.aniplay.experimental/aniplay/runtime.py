import os
import sys
from urllib.parse import parse_qsl
import xbmcaddon
import xbmcvfs
from source import Cache

addon = xbmcaddon.Addon()
root = addon.getAddonInfo('path')
profile = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
os.makedirs(profile, exist_ok=True)
database = os.path.join(profile, 'pages.sqlite')
cache = Cache(database)
handle = int(sys.argv[1])
q = dict(parse_qsl(sys.argv[2].lstrip('?')))
action = q.get('action', 'home')
token = addon.getSetting('token').strip()
image_base = 'https://image.tmdb.org/t/p/'
