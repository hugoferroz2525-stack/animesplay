"""Verificação limitada de HLS: playlist, áudio selecionado e primeiro segmento."""
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from aniplay.streams.validation import MAX_MANIFEST, MediaUnavailable

def attributes(line):
    return {m[1]:m[2] if m[2] is not None else m[3] for m in re.finditer(r'([A-Z0-9-]+)=(?:"([^"]*)"|([^,]*))',line)}

def container(data):
    if any(data[i]==0x47 and data[i+188]==0x47 and data[i+376]==0x47 for i in range(max(0,min(512,len(data)-376)))):return 'mpegts'
    if b'ftyp' in data[:32] or b'styp' in data[:32] or b'moof' in data[:32]:return 'fmp4'
    if data.startswith(b'ID3') or (len(data)>1 and data[0]==255 and data[1]&0xF6==0xF0):return 'aac'
    return ''

class Inspector:
    def __init__(self,stream,opener=None,observe=None,manifest_only=False):
        self.headers=dict(stream.get('headers') or {});self.host=urlsplit(stream['url']).netloc
        self.open=opener.open if opener else urlopen;self.requests=0;self.visited=set()
        self.observe=observe;self.manifest_only=manifest_only
    def read(self,url,limit,manifest=False):
        if urlsplit(url).scheme not in ('https','http') or '{$' in url:
            raise MediaUnavailable('Endereço HLS não reconhecido.','invalid_hls_url')
        self.requests+=1
        if self.requests>9:raise MediaUnavailable('A cadeia de playlists HLS excedeu o limite.','hls_depth')
        headers={k:v for k,v in self.headers.items() if k.lower()!='range'}
        if urlsplit(url).netloc!=self.host:
            headers={k:v for k,v in headers.items() if k.lower() not in ('cookie','authorization')}
        if not manifest:headers['Range']='bytes=0-'+str(limit-1)
        try:response=self.open(Request(url,headers=headers),timeout=12)
        except HTTPError as error:
            if self.observe:
                self.report(error, error.read(512), manifest)
            if manifest or error.code not in (403,405,416) or (self.observe and error.code == 403):
                raise
            error.close();headers.pop('Range',None)
            try:
                response=self.open(Request(url,headers=headers),timeout=12)
            except HTTPError as retry:
                if self.observe:
                    self.report(retry, retry.read(512), manifest)
                raise
        with response:
            data=response.read(limit+1 if manifest else limit)
            if self.observe:
                self.report(response, data, manifest)
            final=response.geturl() if hasattr(response,'geturl') else url
            final=final if isinstance(final,str) else url
            if manifest and len(data)>limit:raise MediaUnavailable('Playlist HLS grande demais.','manifest_too_large')
            if not data or b'<html' in data[:256].lower() or b'<!doctype html' in data[:256].lower():
                raise MediaUnavailable('O servidor devolveu uma página no lugar da mídia HLS.','hls_html')
            return final,data
    def report(self, response, data, manifest):
        content_type = response.headers.get('Content-Type', '') if response.headers else ''
        mime = content_type.split(';', 1)[0].strip().lower()
        if not re.fullmatch(r'[a-z0-9!#$&^_.+-]{1,63}/[a-z0-9!#$&^_.+-]{1,63}', mime):
            mime = ''
        prefix = data.lstrip()[:512].lower()
        self.observe({'stage': 'hls_manifest' if manifest else 'hls_segment',
                      'status': 'response',
                      'http_status': response.getcode() if isinstance(response, HTTPError) else response.status,
                      'content_type': mime,
                      'looks_html': mime in ('text/html', 'application/xhtml+xml')
                                    or b'<html' in prefix or b'<!doctype html' in prefix})
    def playlist(self,url,depth=0,audio=False,initial=None):
        if depth>3 or url in self.visited:raise MediaUnavailable('Playlist HLS circular ou profunda demais.','hls_depth')
        self.visited.add(url)
        if initial is None:
            base,data=self.read(url,MAX_MANIFEST,True)
        else:
            self.requests += 1
            base,data=initial
        if len(data)>MAX_MANIFEST:raise MediaUnavailable('Playlist HLS grande demais.','manifest_too_large')
        if not (data[3:] if data.startswith(b'\xef\xbb\xbf') else data).lstrip().startswith(b'#EXTM3U'):
            raise MediaUnavailable('Playlist HLS inválida.','invalid_manifest')
        lines=[v.strip() for v in data.decode('utf-8-sig').splitlines() if v.strip()]
        variants=[];audios=[]
        for i,line in enumerate(lines):
            if line.startswith('#EXT-X-STREAM-INF:'):
                attrs=attributes(line)
                target=next((v for v in lines[i+1:] if not v.startswith('#')),None)
                if target:variants.append((attrs,urljoin(base,target)))
            elif line.startswith('#EXT-X-MEDIA:'):
                attrs=attributes(line)
                if attrs.get('TYPE')=='AUDIO' and attrs.get('URI'):audios.append(attrs)
        if variants:
            def rank(v):
                try:return int(v[0].get('RESOLUTION','0x0').split('x')[-1]),int(v[0].get('BANDWIDTH',0))
                except ValueError:return 0,0
            attrs,target=max(variants,key=rank);result=self.playlist(target,depth+1,audio)
            selected=[v for v in audios if v.get('GROUP-ID')==attrs.get('AUDIO')]
            if selected:
                chosen=next((v for v in selected if v.get('DEFAULT')=='YES'),selected[0])
                extra=self.playlist(urljoin(base,chosen['URI']),depth+1,True)
                result['is_live']=result['is_live'] or extra['is_live'];result['audio_checked']=not self.manifest_only
            return result
        segment=next((v for v in lines if not v.startswith('#')),None)
        if not segment:raise MediaUnavailable('A playlist não disponibilizou segmentos.','empty_manifest')
        if self.manifest_only:
            return {'is_live': '#EXT-X-ENDLIST' not in lines, 'segments_checked': False}
        keys=[attributes(v) for v in lines if v.startswith('#EXT-X-KEY:')]
        encryption=next((v for v in reversed(keys) if v.get('METHOD')!='NONE'),None)
        if encryption:
            if encryption.get('METHOD')!='AES-128' or encryption.get('KEYFORMAT','identity')!='identity' or not encryption.get('URI'):
                raise MediaUnavailable('Este formato de proteção HLS não é suportado.','unsupported_encryption')
            _,key=self.read(urljoin(base,encryption['URI']),17)
            if len(key)!=16:raise MediaUnavailable('O servidor não entregou a chave HLS válida.','invalid_hls_key')
        _,sample=self.read(urljoin(base,segment),4096)
        kind=container(sample)
        if not kind and not encryption:raise MediaUnavailable('O segmento HLS não contém mídia reconhecida.','invalid_hls_segment')
        if kind=='aac' and not audio:raise MediaUnavailable('A playlist forneceu somente áudio.','audio_only')
        for line in lines:
            if line.startswith('#EXT-X-MAP:'):
                init=attributes(line).get('URI')
                if init:
                    _,data=self.read(urljoin(base,init),4096)
                    if container(data)!='fmp4':raise MediaUnavailable('Inicialização MP4 do HLS inválida.','invalid_hls_init')
        return {'is_live':'#EXT-X-ENDLIST' not in lines,'container':kind or 'aes128','segments_checked':True}

def inspect(stream,opener=None,manifest_only=False,initial=None):
    return Inspector(stream,opener,manifest_only=manifest_only).playlist(stream['url'], initial=initial)
