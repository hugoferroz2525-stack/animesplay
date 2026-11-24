"""Probe pequeno antes de entregar mídia ao Kodi. Não grava URLs temporárias."""
import re
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit

MAX_MANIFEST = 2 * 1024 * 1024
HLS_MIME = 'application/vnd.apple.mpegurl'

class MediaUnavailable(ValueError):
 def __init__(self,message,code='media_unavailable'):
  super().__init__(message);self.code=code

def classify(data,content_type):
 prefix=(data[3:] if data.startswith(b'\xef\xbb\xbf') else data).lstrip()
 lower=prefix[:512].lower();mime=(content_type or '').split(';',1)[0].lower()
 if lower.strip()==b'security error':raise MediaUnavailable('O servidor recusou o acesso ao vídeo.','source_denied')
 if not data:raise MediaUnavailable('O servidor retornou uma resposta vazia.','empty_body')
 if b'ftyp' in data[:32] or b'styp' in data[:32]:return 'video/mp4'
 if prefix.startswith(b'#EXTM3U'):return HLS_MIME
 if b'<MPD' in prefix[:512] or b'<mpd' in lower:return 'application/dash+xml'
 if data.startswith(b'\x1aE\xdf\xa3'):return 'video/webm'
 if mime=='text/html' or any(x in lower for x in (b'<!doctype html',b'<html',b'site unavailable')):
  raise MediaUnavailable('O servidor devolveu uma página de indisponibilidade no lugar do vídeo.','html_response')
 if mime.startswith('audio/'):raise MediaUnavailable('O servidor devolveu somente áudio para este episódio.','audio_only')
 if mime.startswith('video/'):return mime
 raise MediaUnavailable('A resposta não pôde ser reconhecida como mídia.','unknown_media')

def probe(stream,opener=None):
 url=stream.get('url','')
 if urlsplit(url).scheme not in ('http','https'):raise MediaUnavailable('Endereço de mídia inválido.')
 if urlsplit(url).path.lower().endswith('.m3u8'):
  return hls_probe(stream,opener)
 headers={key: value for key,value in (stream.get('headers') or {}).items()
          if key.lower() != 'range'}
 initial = None
 try:
  open_url=opener.open if opener else urlopen
  with open_url(Request(url,headers=headers),timeout=12) as response:
   if response.status not in (200,206):raise MediaUnavailable('Resposta de mídia indisponível.')
   prefix = response.read(2048)
   mime = classify(prefix,response.headers.get('Content-Type',''))
   if mime == HLS_MIME and response.status == 200:
    initial = (response.geturl(), prefix + response.read(MAX_MANIFEST + 1 - len(prefix)))
 except MediaUnavailable:raise
 except HTTPError as error:raise MediaUnavailable('O servidor de vídeo recusou a mídia (HTTP {}).'.format(error.code),'http_'+str(error.code)) from None
 except (TimeoutError,URLError) as error:
  reason = str(getattr(error, 'reason', error))
  blocked = re.match(r'Tunnel connection failed: (\d{3})\b', reason, re.I)
  if blocked:
   code = blocked[1]
   raise MediaUnavailable('A conexão intermediária com o servidor de vídeo retornou HTTP {}.'.format(code),
                          'media_tunnel_' + code) from None
  raise MediaUnavailable('O servidor de vídeo demorou ou falhou ao conectar.','media_connection') from None
 except Exception:raise MediaUnavailable('Não foi possível acessar a mídia neste momento.') from None
 result=dict(stream,mime=mime)
 if mime==HLS_MIME:
  return hls_probe(stream,opener,initial=initial)
 return result


def hls_probe(stream, opener, initial=None):
 from aniplay.streams.hls import inspect
 try:
  return dict(stream, mime=HLS_MIME, **inspect(stream, opener, initial=initial))
 except HTTPError as error:
  raise MediaUnavailable('O servidor recusou a playlist ou segmento HLS (HTTP {}).'.format(error.code),'hls_http_'+str(error.code)) from None
 except (TimeoutError,URLError):
  raise MediaUnavailable('Falha ao ler playlist ou segmento HLS.','hls_connection') from None
