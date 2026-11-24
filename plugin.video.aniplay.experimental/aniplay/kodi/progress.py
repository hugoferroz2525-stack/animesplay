"""Acompanha os episódios do AniPlay após o início da reprodução."""
import json
from contextlib import closing
import sqlite3

import library
from pathlib import Path
import time
from threading import RLock


import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from aniplay.storage.history import History, PENDING, media_key
from aniplay.storage.userdata import connect


class EpisodePlayer(xbmc.Player):
    def __init__(self, history, window):
        super().__init__()
        self.history = history
        self.window = window
        self.active = None
        self.lock = RLock()
        self.autoplay = False
        self.skip = ()
        self.intervals = None
        self.used = set()
        self.up_next = None
        self.resume_target = None
        self.resume_duration = None
        self.mode = 'button'
        self.button = None

    def onAVStarted(self):
        self.finish()
        with self.lock:
            self.up_next = None
        try:
            pending = json.loads(self.window.getProperty(PENDING) or '{}')
            key = media_key(self.getPlayingFile())
            if key not in pending.get('keys', ()) or pending.get('expires', 0) < time.time():
                return
            self.window.clearProperty(PENDING)
            with self.lock:
                self.active = (key, pending['item'], 0, 0)
                self.autoplay = pending.get('autoplay') is True
                self.skip = pending.get('skip', ())
                self.intervals = None
                self.external = pending.get('aniskip')
                self.skip_enabled = pending.get('skip_enabled',False)
                self.mode = pending.get('skip_mode','auto')
                self.allowed = pending.get('allowed',[])
                self.used.clear()
            offset = pending.get('resume',0)
            with self.lock:
                self.resume_target=offset if type(offset) in (int,float) and 0<offset and not pending.get('is_live',False) else None
                self.resume_duration=None
        except (ValueError, TypeError, KeyError, RuntimeError):
            return
        try:
            episode = pending['item']
            with closing(connect(self.history.path.with_name('pages.sqlite'))) as db:
                library.initialize(db)
                library.save(db, 'recent', episode['url'], episode['title'], episode.get('icon', ''))
        except (OSError, sqlite3.Error):
            xbmc.log('AniPlay: falha ao gravar histórico recente', xbmc.LOGWARNING)

    def sample(self):
        active = self.active
        if not active:
            self.tick_button()
            return
        try:
            key, item, _, _ = active
            if not self.isPlayingVideo() or media_key(self.getPlayingFile()) != key:
                self.tick_button()
                return
            sample = (key, item, self.getTime(), self.getTotalTime())
            with self.lock:
                if self.active is active:
                    self.active = sample
            if not self.resume_if_ready(sample):self.skip_interval(sample)
            self.tick_button(sample[2])
        except RuntimeError:
            pass

    def show_button(self, kind, end, total):
        from aniplay.kodi.skipbutton import SkipButton
        self.close_button()
        path = xbmcaddon.Addon('plugin.video.aniplay.experimental').getAddonInfo('path')
        target = min(end, total - 0.2)
        label = 'Pular abertura' if kind == 'op' else 'Pular encerramento'
        dialog = SkipButton('aniplay-skip.xml', path, 'Default', '1080i',
                            label=label, on_skip=lambda: self.seekTime(target))
        with self.lock:
            self.button = (dialog, end)
        dialog.show()

    def tick_button(self, position=None):
        with self.lock:
            current = self.button
        if current and (position is None or position >= current[1] - 1):
            self.close_button()

    def close_button(self):
        with self.lock:
            current, self.button = self.button, None
        if current:
            try:
                current[0].close()
            except Exception:
                pass

    def resume_if_ready(self,sample):
        with self.lock:
            target=self.resume_target
            if target is None:return False
            position,duration=sample[2:]
            if position>10 or duration<=target+5:
                if duration>0:self.resume_target=None
                return False
            if self.resume_duration is None or abs(self.resume_duration-duration)>2:
                self.resume_duration=duration;return True
            self.resume_target=None
        if not xbmc.getCondVisibility('Player.SeekEnabled'):return False
        self.seekTime(target)
        return True

    def skip_interval(self, sample):
        if sample[3] <= 0:
            return
        if self.intervals is None:
            intervals = list(self.skip)
            if self.external and any(k not in {i[0] for i in intervals} for k in self.allowed):
                from aniplay.streams.aniskip import lookup
                try:
                    fetched = lookup(*self.external,sample[3])
                    intervals.extend(i for i in fetched if i[0] in self.allowed and i[0] not in {v[0] for v in intervals})
                except (OSError,ValueError):
                    pass
            with self.lock:
                if self.active is not sample:
                    return
                self.intervals = intervals
                if self.skip_enabled and not any(i[0]=='op' for i in intervals):
                    from aniplay.flix_ui import notification
                    notification('Use “Ajustar abertura” no menu do episódio.','Abertura sem marcação','skip')
        hit = None
        with self.lock:
            if self.active is not sample:
                return
            for kind, start, end in self.intervals:
                if (kind not in self.used and 0 <= start <= sample[2] < end - 1
                        and end <= sample[3] and xbmc.getCondVisibility('Player.SeekEnabled')):
                    self.used.add(kind)
                    hit = (kind, end, sample[3])
                    break
        if not hit:
            return
        kind, end, total = hit
        if self.mode == 'auto':
            self.seekTime(min(end, total - 0.2))
            from aniplay.flix_ui import notification
            notification('Reprodução em %d:%02d.' % divmod(int(end),60),'Abertura pulada' if kind=='op' else 'Encerramento pulado','skip')
        else:
            self.show_button(kind, end, total)

    def save(self, ended=False):
        with self.lock:
            if self.active:
                _, item, position, duration = self.active
                try:
                    self.history.save(item, position, duration, ended)
                except Exception:
                    xbmc.log('AnimesPlay: falha ao gravar progresso', xbmc.LOGWARNING)

    def finish(self, ended=False):
        self.close_button()
        with self.lock:
            self.save(ended)
            self.active = None
            self.resume_target=None
            self.resume_duration=None

    def onPlayBackEnded(self):
        with self.lock:
            self.finish(ended=True)

    def onPlayBackStopped(self):
        with self.lock:
            self.up_next = None
            self.finish()

    def onPlayBackError(self):
        self.onPlayBackStopped()


def run():
    addon = xbmcaddon.Addon('plugin.video.aniplay.experimental')
    profile = Path(xbmcvfs.translatePath(addon.getAddonInfo('profile')))
    player = EpisodePlayer(History(profile), xbmcgui.Window(10000))
    monitor = xbmc.Monitor()
    next_index = time.monotonic()+30
    last_save = time.monotonic()
    from concurrent.futures import ThreadPoolExecutor
    from aniplay.poster_badges import pending_job, pillow, process

    with ThreadPoolExecutor(max_workers=2) as workers:
        jobs = {}
        while not monitor.waitForAbort(1):
            jobs = {job: future for job, future in jobs.items() if not future.done()}
            if len(jobs) < 2 and pillow():
                job = pending_job(profile, exclude=jobs)
                if job:
                    jobs[job] = workers.submit(process, job)
            if time.monotonic()>=next_index and not player.isPlaying():
                xbmc.executebuiltin("RunPlugin(plugin://plugin.video.aniplay.experimental/?action=index_update)")
                next_index=time.monotonic()+180
            player.sample()
            if time.monotonic() - last_save >= 10:
                player.save()
                last_save = time.monotonic()
    player.finish()


if __name__ == '__main__':
    run()
