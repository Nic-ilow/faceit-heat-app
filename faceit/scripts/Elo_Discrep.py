import requests
import logging
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from django.core.cache import cache
from faceit.scripts.headers import headers

logger = logging.getLogger(__name__)

ELO_CACHE_TTL = 3600  # 1 hour

_session = None

def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.5,
            backoff_jitter=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        _session.mount('http://', adapter)
        _session.mount('https://', adapter)
    return _session


class EloCalculator:

    @staticmethod
    def find_game_key(player_details):
        if 'cs' in player_details['games']:
            return 'cs'
        if 'csgo' in player_details['games']:
            return 'csgo'
        for key in player_details['games'].keys():
            if 'cs' in key.lower():
                return key
        if player_details['games']:
            return list(player_details['games'].keys())[0]
        return None

    @staticmethod
    def get_player_elo(player_id):
        cache_key = f"player_elo:{player_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            player_details = _get_session().get(
                f'https://open.faceit.com/data/v4/players/{player_id}',
                headers=headers,
                timeout=10,
            ).json()

            game_key = EloCalculator.find_game_key(player_details)
            elo = float(player_details['games'][game_key]['faceit_elo'])

            cache.set(cache_key, elo, timeout=ELO_CACHE_TTL)
            return elo
        except Exception as e:
            logger.error(f"Error getting player ELO: {e}")
            cache.set(cache_key, 1500, timeout=ELO_CACHE_TTL)
            return 1500

    @staticmethod
    def calculate_discrepancy(all_stats, player_team, player_elo):
        enemy_team = abs(player_team - 1)
        try:
            enemy_players = all_stats['rounds'][0]['teams'][enemy_team]['players']

            enemy_elo = 0
            for player in enemy_players:
                enemy_elo += EloCalculator.get_player_elo(player['player_id'])

            enemy_avg_elo = enemy_elo / len(enemy_players)
            discrepancy = enemy_avg_elo - player_elo
            return discrepancy

        except Exception as e:
            logger.error(f"Error calculating ELO discrepancy: {e}")
            return 0


def elo_discrep(all_stats, p_team, p_elo):
    return EloCalculator.calculate_discrepancy(all_stats, p_team, p_elo)
