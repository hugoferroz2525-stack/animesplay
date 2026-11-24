import re
import traceback
import xbmc
import xbmcgui
import xbmcplugin
from aniplay.runtime import action, cache, handle
from aniplay.navigation import recovery, run

try:
    run()
except Exception as exc:
    diagnostic = re.sub(r'https?://[^\s]+', '<URL>', traceback.format_exc())
    diagnostic = re.sub(r'(?i)(api_key=|Bearer )[^\s&]+', r'\1<oculto>', diagnostic)
    xbmc.log('AniPlay: '+diagnostic, xbmc.LOGERROR)
    message = 'Falha ao carregar'
    if getattr(exc,'code',None) == 429:
        seconds = exc.headers.get('Retry-After','')
        message = 'Limite temporário do servidor'
        if seconds.isdigit():
            message += ' · Tente em '+seconds+' s'
    from aniplay.flix_ui import notification
    notification(message,icon='alert')
    if action=='play':
        xbmcplugin.setResolvedUrl(handle,False,xbmcgui.ListItem())
    else:
        from aniplay import views
        views.pending_items.clear()
        recovery(message)
        views.flush()
        xbmcplugin.endOfDirectory(handle,cacheToDisc=False)
finally:
    cache.user.close()
    cache.db.close()
