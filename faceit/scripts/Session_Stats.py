import requests
import logging
import time
from faceit.scripts.headers import headers
from faceit.scripts.stat_finder import StatFinder
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


def get_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        backoff_jitter=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


class SessionAnalyzer:

    def __init__(self, player_id, nickname, configured_time):
        self.player_id = player_id
        self.nickname = nickname
        self.configured_time = configured_time
        self.from_time = int(configured_time - (60 * 60 * 24))
        self.to_time = int(configured_time)
        self.session = get_session()

    def _fetch_history(self, params):
        response = self.session.get(
            f'https://open.faceit.com/data/v4/players/{self.player_id}/history',
            params=params,
            headers=headers,
            timeout=15
        )
        return response.json()

    def _try_stats(self, history):
        if 'items' in history and len(history['items']) > 0:
            stats = StatFinder.get_player_stats(history, self.nickname)
            if stats[5]:  # data_available flag
                return stats
        return None

    def analyze(self):
        start_time = time.time()

        # 1. Try without game filter
        try:
            history = self._fetch_history({
                'from': self.from_time,
                'to': self.to_time,
                'limit': 50
            })
            stats = self._try_stats(history)
            if stats:
                logger.info(f"Stats for {self.nickname} in {time.time() - start_time:.2f}s (no filter)")
                return stats
        except Exception as e:
            logger.error(f"History without game filter failed for {self.nickname}: {e}")

        # 2. Try with specific game IDs
        for game_id in ['cs2', 'csgo', 'cs']:
            try:
                history = self._fetch_history({
                    'game': game_id,
                    'from': self.from_time,
                    'to': self.to_time,
                    'limit': 50
                })
                stats = self._try_stats(history)
                if stats:
                    logger.info(f"Stats for {self.nickname} in {time.time() - start_time:.2f}s (game={game_id})")
                    return stats
            except Exception as e:
                logger.error(f"History with game={game_id} failed for {self.nickname}: {e}")

        # 3. Try extended 30-day window
        try:
            history = self._fetch_history({
                'from': int(self.configured_time - (86400 * 30)),
                'to': self.to_time,
                'limit': 100
            })
            stats = self._try_stats(history)
            if stats:
                logger.info(f"Stats for {self.nickname} in {time.time() - start_time:.2f}s (30-day window)")
                return stats
        except Exception as e:
            logger.error(f"Extended history failed for {self.nickname}: {e}")

        # 4. Direct single-match fallback
        try:
            if 'items' in history and len(history['items']) > 0:
                match_id = history['items'][0]['match_id']
                match_stats = requests.get(
                    f'https://open.faceit.com/data/v4/matches/{match_id}/stats',
                    headers=headers,
                    timeout=15
                ).json()

                for team in match_stats['rounds'][0]['teams']:
                    for player in team['players']:
                        if player['nickname'].lower() == self.nickname.lower():
                            k = float(player['player_stats']['Kills'])
                            d = float(player['player_stats']['Deaths'])
                            if d == 0:
                                d = 1
                            kd = k / d
                            kr = float(player['player_stats']['K/R Ratio'])
                            return [kd, kr, 1, 0, kd * 1.5, True]

        except Exception as e:
            logger.error(f"Direct match analysis failed for {self.nickname}: {e}")

        duration = time.time() - start_time
        logger.warning(f"No valid stats for {self.nickname} after {duration:.2f}s")
        return [1.0, 0.72, 0, 0, 0.0, False]

    @classmethod
    def get_session_stats(cls, player_id, nickname, configured_time):
        analyzer = cls(player_id, nickname, configured_time)
        return analyzer.analyze()


def session(p_id, nick, configured_time):
    return SessionAnalyzer.get_session_stats(p_id, nick, configured_time)
