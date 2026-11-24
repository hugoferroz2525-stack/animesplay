import time
import unittest
from unittest.mock import patch

import kodi_stub as k
from aniplay import episode_context, metadata, multisite as m, navigation, playback, runtime as rt, views
from aniplay.providers import quality
from aniplay.providers.scraper import Page, Resolver
from aniplay.storage.history import History
from source import BASE, Cache

HINATA = 'https://www.hinatasoul.com'
URL = HINATA + '/animes/birdie-wing-golf-girls-story'
SRC = dict(site='HinataSoul', title='Birdie Wing', url=URL, audio='', season=None)


class EpisodeListing(unittest.TestCase):
    def setUp(self):
        rt.q.clear()
        rt.q.update(site=SRC['site'], url=URL, sources=m.encode([SRC]), title=SRC['title'])
        views.pending_items.clear()

    def listing(self, *labels, complete=True):
        return m.EpisodeList([(f'Episódio {label}', f'{HINATA}/videos/{i + 10000}', '')
                              for i, label in enumerate(labels)], complete)

    def test_partial_page_is_not_saved_as_a_complete_snapshot(self):
        alt = URL + '/page/2'
        out = ([('Episódio 1', HINATA + '/videos/10000', '')], alt, '2')
        with patch.object(m, 'page', side_effect=['one', OSError]), patch.object(m, 'extrair_episodios', return_value=out):
            rows = m.load_episodes('HinataSoul', URL)
        self.assertFalse(rows.complete)
        self.assertEqual(len(rows), 1)

    def test_fallback_preserves_actual_order_and_distinct_urls(self):
        items = self.listing(6, 1, 1, 0, 'especial')
        src = dict(SRC, url=HINATA + '/animes/e1eaa4181415abd4e16cce073629ee329ebd3200')
        with patch.object(m, 'load_episodes', return_value=items):
            result = m.variant_rows([src], {})
        self.assertEqual(list(result), [None])
        self.assertEqual([options[0]['url'] for options in result[None]], [row[1] for row in items])
        self.assertTrue(all(not options[0]['mapped'] for options in result[None]))

    def test_count_is_in_both_labels_and_uses_actual_urls(self):
        rows = self.listing(1, 2, 3)
        History(rt.profile).save(dict(id=rows[0][1], url=rows[0][1], title='Episódio 1'), 95, 100)
        with patch.object(m, 'lookup', return_value={'media_type': 'tv', 'id': 137390}), \
                patch.object(m, 'provider_season_sources', return_value=[SRC]), \
                patch.object(m, 'load_episodes', return_value=rows):
            m.seasons()
        li = views.pending_items[-1][1]
        self.assertEqual(li.label, 'Temporada 1 (3 eps)')
        self.assertEqual(li.tag.calls['setTitle'], ('Temporada 1 (3 eps)',))
        self.assertEqual(li.props['TotalEpisodes'], '3')
        self.assertEqual(li.props['WatchedEpisodes'], '1')

    def test_partial_source_list_is_paginated_without_a_total(self):
        rows = self.listing(*range(1, 26), complete=False)
        with patch.object(m, 'lookup', return_value={}), patch.object(m, 'provider_season_sources', return_value=[SRC]), \
                patch.object(m, 'load_episodes', return_value=rows), patch.object(m, 'season_details', return_value={}):
            m.seasons()
        self.assertEqual(len(views.pending_items), 25)
        self.assertEqual(views.pending_items[-1][1].label, 'Próxima página')
        self.assertNotIn('TotalEpisodes', views.pending_items[0][1].props)

    def test_unmapped_url_does_not_restore_old_episode_association(self):
        url = HINATA + '/videos/4466'
        with rt.cache.db:
            episode_context.remember(dict(url=url, showid=1, season=1, local=9), {'id': 554}, None, '')
        self.assertEqual(episode_context.restore(dict(url=url, source_order='1')), {})


class QualitySelector(unittest.TestCase):
    def setUp(self):
        k.records.clear()
        self.page = Page(HINATA + '/videos/50001', '')
        self.options = [('720p', 'player', '8'), ('Player 2', 'player', '4'), ('Player 3', 'player', '2')]

    def test_confirmed_quality_not_player_ordinal_and_cache_is_scoped(self):
        def measured(page, kind, value, deadline):
            return {'4': '1080p', '2': '480p'}[value]
        with patch.object(quality, 'measure_choice', side_effect=measured) as probe:
            first = quality.player_labels(self.page, self.options, rt.cache)
            second = quality.player_labels(self.page, self.options, rt.cache)
            self.assertEqual(probe.call_count, 2)
        self.assertEqual(first, second)
        self.assertEqual(first, ['Player 1: [COLOR yellow]HD[/COLOR]',
                                 'Player 2: [COLOR yellow]Full HD[/COLOR]',
                                 'Player 3: [COLOR yellow]SD[/COLOR]'])

    def test_deadline_leaves_unconfirmed_choices_available(self):
        page = Page(HINATA + '/videos/50002', '')
        def slow(*args):
            time.sleep(.15)
            return '1080p'
        with patch.object(quality, 'WAIT_SECONDS', .02), patch.object(quality, 'measure_choice', side_effect=slow):
            start = time.monotonic()
            labels = quality.player_labels(page, self.options, rt.cache)
            self.assertLess(time.monotonic() - start, .12)
        self.assertEqual(labels[1:], ['Player 2', 'Player 3'])

    def test_selection_keeps_episode_audio_and_resolves_only_chosen_variant(self):
        choices = [('360p', 'player', '2'), ('720p', 'player', '0'), ('1080p', 'player', '1')]
        rt.q.clear()
        rt.q.update(url=self.page.url, preferred_audio='Dublado')
        k.records['choice'] = 1
        with patch.object(Resolver, 'episode_page', return_value=self.page), \
                patch('aniplay.providers.scraper.quality_choices', return_value=choices), \
                patch.object(quality, 'resolve_choice') as resolver, patch.object(playback, 'finish_playback'):
            def resolved(instance, page, kind, value):
                instance.verification = (206, 'video/mp4')
                return 'https://example.com/video.mp4'
            resolver.side_effect = resolved
            playback.play_provider()
        self.assertEqual(resolver.call_args.args[1:], (self.page, 'player', '0'))
        self.assertEqual(rt.q['url'], self.page.url)
        self.assertEqual(rt.q['preferred_audio'], 'Dublado')

    def test_cancel_quality_never_resolves_a_candidate(self):
        rt.q.clear()
        rt.q.update(url=self.page.url, preferred_audio='Legendado')
        k.records['choice'] = -1
        with patch.object(Resolver, 'episode_page', return_value=self.page), \
                patch('aniplay.providers.scraper.quality_choices', return_value=[('360p', 'player', '0'), ('720p', 'player', '1')]), \
                patch.object(quality, 'resolve_choice') as resolver:
            playback.play_provider()
        resolver.assert_not_called()
        self.assertEqual(k.records.get('resolved'), [False])
        self.assertEqual(rt.q['preferred_audio'], 'Legendado')


class DataProtection(unittest.TestCase):
    def test_cache_purge_preserves_favorites_watched_resume(self):
        import library
        library.initialize(rt.cache.user)
        favorite = BASE + '/anime/favorito-teste'
        library.save(rt.cache.user, 'favorites', favorite, 'Teste', '')
        history = History(rt.profile)
        watched = HINATA + '/videos/99991'
        playing = HINATA + '/videos/99992'
        history.save(dict(id=watched, url=watched, title='Visto'), 99, 100)
        history.save(dict(id=playing, url=playing, title='Retomada'), 30, 100)
        for scope in ('pages', 'tmdb'):
            rt.q.clear()
            rt.q.update(scope=scope)
            navigation.handle_purge()
        self.assertTrue(any(row[0] == favorite for row in library.contents(rt.cache.user, 'favorites')))
        self.assertTrue(history.progress_for([watched])[watched][2])
        self.assertEqual(history.resume(playing), 30)


if __name__ == '__main__':
    unittest.main()
