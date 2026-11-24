import unittest
from unittest.mock import patch

import kodi_stub as kodi
from aniplay import metadata, multisite as multi, playback, runtime as runtime
from aniplay.providers.grouping import identity
from aniplay.providers.scraper import NoPlayerMedia, Page, Resolver, ScraperError
from aniplay.videotag import episode_fields

HINATA = 'https://www.hinatasoul.com'
BAKASHI = 'https://bakashi.top'
TUBE = 'https://www.anitube22.vip'


class AudioPlayback(unittest.TestCase):
    def setUp(self):
        kodi.records.clear()
        runtime.q.clear()
        runtime.q.update(url=f'{BAKASHI}/ep/one-piece-1-episodio-1')

    def play(self, groups, choice, expected, expected_dialog):
        kodi.records['choice'] = choice
        with patch.object(runtime.cache, 'get', return_value=''), \
                patch.object(playback, 'audio_sources', return_value=groups), \
                patch.object(playback, 'player_buttons', return_value=[]), \
                patch.object(playback, 'resolve_audio', side_effect=lambda _, audio, __:
                             (audio, 'https://example.com/video.mp4', (), 'video/mp4', 'https://example.com')), \
                patch.object(playback, 'finish_playback') as finish:
            playback.play()
        self.assertEqual(bool(kodi.records.get('dialogs')), expected_dialog)
        if expected:
            self.assertEqual(finish.call_args.args[0], expected)
        else:
            finish.assert_not_called()
            self.assertEqual(kodi.records.get('resolved'), [False])

    def test_missing_dub_requires_confirmation_even_with_one_option(self):
        runtime.q['preferred_audio'] = 'Dublado'
        self.play({'Legendado': ['player']}, -1, None, True)

    def test_missing_dub_can_explicitly_accept_subtitles(self):
        runtime.q['preferred_audio'] = 'Dublado'
        self.play({'Legendado': ['player']}, 0, 'Legendado', True)

    def test_requested_subtitles_are_preserved(self):
        runtime.q['preferred_audio'] = 'Legendado'
        self.play({'Dublado': ['player'], 'Legendado': ['player']}, -1, 'Legendado', False)

    def test_missing_all_options_does_not_resolve(self):
        runtime.q['preferred_audio'] = 'Dublado'
        self.play({}, -1, None, False)
        self.assertTrue(kodi.records.get('notices'))

    def test_failure_of_selected_stream_can_be_cancelled(self):
        kodi.records['choice'] = -1
        with patch.object(playback, 'media', side_effect=ValueError):
            self.assertIsNone(playback.resolve_audio({'Dublado': ['player']}, 'Dublado', ['Legendado']))
        self.assertEqual(kodi.records.get('resolved'), [False])

    def test_filter_propagates_bakashi_edition_to_season_route(self):
        runtime.q.update(edition='Dublado', title='One Piece', sources=multi.encode([
            {'site': 'Bakashi', 'url': f'{BAKASHI}/anime/one-piece-dublado', 'audio': 'Dublado'},
        ]))
        with patch('aniplay.catalog.catalog_metadata', return_value=[{}]), patch.object(multi, 'item') as item:
            multi.servers()
        self.assertEqual(item.call_args.args[2]['preferred_audio'], 'Dublado')


class PlayerPage(unittest.TestCase):
    def test_empty_player_html_is_classified_separately(self):
        page = Page(f'{TUBE}/video/492294', '<html><title>Player</title></html>')
        with self.assertRaises(NoPlayerMedia):
            Resolver().get_player(page)

    def test_network_error_is_not_reported_as_empty_html(self):
        page = Page(f'{TUBE}/video/492294', '<video src="https://example.org/492294.mp4"></video>')
        resolver = Resolver()
        with patch.object(resolver, '_validate', side_effect=ScraperError('HTTP 404')):
            with self.assertRaisesRegex(ScraperError, '404') as error:
                resolver.get_player(page)
        self.assertNotIsInstance(error.exception, NoPlayerMedia)

    def test_kodi_notification_after_empty_player(self):
        runtime.q.clear()
        runtime.q.update(url=f'{TUBE}/video/492294')
        kodi.records.clear()
        with patch.object(Resolver, 'episode_page', return_value=Page(runtime.q['url'], '<html></html>')):
            playback.play_provider()
        self.assertIn('não enviou uma fonte de vídeo', kodi.records['notices'][0][1])
        self.assertEqual(kodi.records['resolved'], [False])


class CatalogMapping(unittest.TestCase):
    def source(self, slug, season=None, audio=''):
        return dict(site='HinataSoul', url=f'{HINATA}/animes/{slug}', season=season, audio=audio, title='Teste')

    def rows(self, *numbers):
        return [(f'Episódio {n:02d}', f'{HINATA}/videos/{i + 100}', '') for i, n in enumerate(numbers)]

    def test_digimon_ids_do_not_merge(self):
        urls = [f'{BAKASHI}/anime/digimon-adventure-1a-temporada',
                f'{BAKASHI}/anime/digimon-adventure-2020-1a-temporada',
                f'{HINATA}/animes/3ffe62e3b6aac35030469cf85cec7fd55bf2b726']
        self.assertEqual([metadata.reference(url, runtime.cache)[1] for url in urls], [31654, 98034, 31654])
        rows = [('Bakashi', 'Digimon Adventure', urls[0], ''), ('Bakashi', 'Digimon Adventure (2020)', urls[1], ''),
                ('HinataSoul', 'Digimon Adventure', urls[2], '')]
        self.assertEqual([g.key for g in multi.grouped(rows)], ['tv:31654', 'tv:98034'])

    def test_audio_evidence_from_item_slug_and_section_is_conservative(self):
        self.assertEqual(identity('Dai Sentai Goggle-V', f'{TUBE}/tokusatsu/goggle-five-v-legendado')[1], 'Legendado')
        self.assertEqual(identity('One Piece', f'{TUBE}/anime/one-piece')[1], '')
        self.assertEqual(identity('One Piece', f'{TUBE}/animes-dublado/abc')[1], 'Dublado')
        self.assertEqual(identity('One Piece Legendado', f'{TUBE}/animes-dublado/abc')[1], 'Legendado')

    def test_birdie_wing_uses_14_to_25_in_season_one(self):
        src = self.source('birdie-wing-golf-girls-story-season-2', 2)
        with patch.object(multi, 'load_episodes', return_value=self.rows(*range(1, 13))):
            rows = multi.variant_rows([src], {})
        self.assertEqual(list(rows), [1])
        self.assertEqual([int(x[0]['local']) for x in rows[1]], list(range(14, 26)))
        self.assertEqual(rows[1][0][0]['raw'], '1')
        self.assertEqual(rows[1][0][0]['url'], f'{HINATA}/videos/100')
        self.assertEqual(episode_fields(dict(season=1, local='14', raw='1'))['episode'], 14)

    def test_birdie_partner_is_opened_from_single_segment(self):
        src = self.source('birdie-wing-golf-girls-story-season-2', 2)
        with patch.object(multi, 'page', side_effect=OSError):
            rows = multi.provider_season_sources([src])
        self.assertTrue(any(r['url'].endswith('/birdie-wing-golf-girls-story') for r in rows))

    def test_slime_stays_in_season_two_without_mapping_episode_zero(self):
        first = self.source('b6146d534fea1df93fb331751c95534c561b29bd')
        second = self.source('aaf08754be3b5dab97813591436ce7954c7c182c')
        with patch.object(multi, 'load_episodes', return_value=self.rows(*range(13))):
            rows = multi.variant_rows([second], {})
        self.assertEqual([int(r[0]['local']) for r in rows[2] if r[0]['mapped']], list(range(13, 25)))
        self.assertEqual(rows[2][0][0]['raw'], '0')
        self.assertFalse(rows[2][0][0]['mapped'])
        grouped = multi.grouped([('HinataSoul', '2nd Season', first['url'], ''),
                                 ('HinataSoul', '2nd Season Part 2', second['url'], '')])
        self.assertEqual([group.key for group in grouped], ['tv:82684'])

    def test_one_piece_preserves_both_urls_for_same_number(self):
        src = self.source('e1eaa4181415abd4e16cce073629ee329ebd3200')
        seasons = {'seasons': [{'season_number': 1, 'episode_count': 1},
                               {'season_number': 2, 'episode_count': 3}]}
        with patch.object(multi, 'load_episodes', return_value=self.rows(1, 2, 2, 3)):
            rows = multi.variant_rows([src], seasons)
        self.assertEqual([r[0]['url'] for r in rows[2] if not r[0]['mapped']], [f'{HINATA}/videos/101', f'{HINATA}/videos/102'])
        self.assertEqual(rows[2][-1][0]['raw'], '3')

    def test_two_cosmos_parts_send_movie_tags(self):
        src = self.source('bishoujo-senshi-sailor-moon-cosmos-movie')
        with patch.object(multi, 'load_episodes', return_value=self.rows(1, 2)), \
                patch.object(metadata, 'details', return_value={}):
            films = list(multi.cosmos_films([src], 'Sailor Moon Cosmos', ''))
        self.assertEqual([params['movie_id'] for _, params, _ in films], [968868, 968870])
        self.assertEqual([episode_fields(params) for _, params, _ in films], [{'mediatype': 'movie'}] * 2)


if __name__ == '__main__':
    unittest.main()
