from types import ModuleType
from pathlib import Path
import sys,tempfile
root=Path(__file__).resolve().parents[1]/'plugin.video.aniplay.experimental'
sys.path.insert(0,str(root))
tmp=tempfile.TemporaryDirectory()
profile=tmp.name
records={}
default={'tmdb_language':'pt-BR','tmdb_days':7,'skip_mode':'Desligado'}
settings=dict(default)
def log(key,value):records.setdefault(key,[]).append(value)
class Sink:
 def __init__(self):self.calls={}
 def __getattr__(self,n):
  def call(*a,**k):self.calls[n]=a
  return call
class ListItem(Sink):
 def __init__(self,*a,**k):
  super().__init__();self.label=k.get('label',a[0] if a else '');self.tag=Sink();self.props={}
 def getVideoInfoTag(self):return self.tag
 def setProperty(self,k,v):self.props[k]=v
class Dialog:
 def select(self,title,items,**kw):log('dialogs',[title,items]);return records.get('choice',-1)
 def notification(self,*a,**k):log('notices',a[:2])
 def yesno(self,*a,**k):return True
 def info(self,item):log('info',item)
class Addon:
 def getAddonInfo(self,n):return str(root) if n=='path' else profile
 def getSetting(self,n):return str(settings.get(n,''))
 def getSettingBool(self,n):return bool(settings.get(n,False))
 def getSettingInt(self,n):return int(settings.get(n,0))
 def openSettings(self):log('settings',True)
def mod(n,**vals):
 m=ModuleType(n);m.__dict__.update(vals);sys.modules[n]=m
mod('xbmc',LOGWARNING=2,LOGINFO=1,LOGERROR=3,log=lambda *a:None,executebuiltin=lambda a:log('builtin',a),getInfoLabel=lambda _: '21.2',getCondVisibility=lambda _:False,Actor=lambda *a:a)
mod('xbmcgui',Dialog=Dialog,ListItem=ListItem,Window=lambda *_:Sink(),DialogProgress=Sink)
mod('xbmcplugin',addDirectoryItems=lambda h,a,n:log('items',list(a)),addDirectoryItem=lambda *a:log('item',a),setResolvedUrl=lambda _,ok,li:log('resolved',ok),setPluginCategory=lambda *a:None,setContent=lambda *a:None,addSortMethod=lambda *a:None,endOfDirectory=lambda *a,**k:None,SORT_METHOD_NONE=0,SORT_METHOD_EPISODE=1,SORT_METHOD_VIDEO_SORT_TITLE=2)
mod('xbmcvfs',translatePath=lambda p:p)
mod('xbmcaddon',Addon=Addon)
sys.argv=['plugin://plugin.video.aniplay.experimental/','1','']
