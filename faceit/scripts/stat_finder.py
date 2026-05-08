import requests
import logging
import numpy as np
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from django.core.cache import cache

from faceit.scripts.headers import headers
from faceit.scripts.Elo_Discrep import EloCalculator
from faceit.scripts.Performance_Calc import PerformanceCalculator

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


class StatFinder:

    def __init__(self, history, nickname):
        self.history = history
        self.nickname = nickname
        self.match_count = min(10, len(history.get('items', [])))
        self.num_wins = 0
        self.tot_k = 0
        self.tot_d = 0
        self.tot_kr = 0
        self.perf_scores = []
        self.player_team = 0
        self.player_elo = 0
        self.session = get_session()

    def _get_match_stats(self, match_id):
        cache_key = f"match_stats:{match_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for match stats {match_id}")
            return cached

        response = self.session.get(
            f'https://open.faceit.com/data/v4/matches/{match_id}/stats',
            headers=headers,
            timeout=10
        )
        data = response.json()
        cache.set(cache_key, data, timeout=None)
        return data

    def process_match(self, match_num):
        start_time = time.time()
        try:
            match_item = self.history['items'][match_num]
            match_id = match_item['match_id']

            all_stats = self._get_match_stats(match_id)

            team1_id = match_item.get('teams', {}).get('faction1', {}).get('team_id', '')

            if not team1_id and 'rounds' in all_stats and len(all_stats['rounds']) > 0:
                teams = [0, 1]
            else:
                teams = [0, 1] if all_stats['rounds'][0]['teams'][0]['team_id'] == team1_id else [1, 0]

            k, d, kr, kd = 0, 0, 0, 0
            player_found = False

            for team in teams:
                for player in all_stats['rounds'][0]['teams'][team]['players']:
                    if self.nickname.lower() == player['nickname'].lower():
                        player_found = True
                        player_stats = player.get('player_stats', {})
                        k = float(player_stats.get('Kills', 0))
                        d = float(player_stats.get('Deaths', 1))
                        if d == 0:
                            d = 1
                        kd = k / d
                        kr = float(player_stats.get('K/R Ratio', 0))
                        self.player_team = int(team)

                        team_stats = all_stats['rounds'][0]['teams'][team].get('team_stats', {})
                        self.num_wins += int(team_stats.get('Team Win', 0))

                        if match_num == 0:
                            player_id = player['player_id']
                            self.player_elo = EloCalculator.get_player_elo(player_id)

            if player_found:
                discrep = EloCalculator.calculate_discrepancy(all_stats, self.player_team, self.player_elo)
                self.tot_k += k
                self.tot_d += d
                self.tot_kr += kr
                perf_score = PerformanceCalculator.calculate(kd, kr, discrep)
                self.perf_scores.append(perf_score)

                duration = time.time() - start_time
                logger.info(f"Match {match_id} processed in {duration:.2f}s - KD: {kd:.2f}, KR: {kr:.2f}, Perf: {perf_score:.2f}")
                return True
            else:
                logger.warning(f"Player {self.nickname} not found in match {match_id}")
                return False

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error processing match {match_num} after {duration:.2f}s: {e}")
            return False

    def analyze(self):
        if self.match_count == 0:
            logger.warning(f"No matches found for player {self.nickname}")
            return [1.0, 0.72, 0, 0, 0.0, False]

        max_matches = min(10, self.match_count)
        success_count = 0
        for i in range(max_matches):
            try:
                if self.process_match(i):
                    success_count += 1
                if success_count >= 3:
                    break
            except Exception as e:
                logger.error(f"Error in match processing: {e}")

        if self.tot_d == 0:
            self.tot_d = 1

        if len(self.perf_scores) == 0:
            logger.warning(f"No valid matches processed for {self.nickname}")
            return [1.0, 0.72, 0, 0, 1.0, False]

        tot_kd = self.tot_k / self.tot_d
        tot_kr = self.tot_kr / max(1, len(self.perf_scores))
        avg_perf_score = float(np.mean(self.perf_scores))

        return [tot_kd, tot_kr, len(self.perf_scores), self.num_wins, avg_perf_score, True]

    @classmethod
    def get_player_stats(cls, history, nickname):
        try:
            finder = cls(history, nickname)
            return finder.analyze()
        except Exception as e:
            logger.error(f"Error in get_player_stats for {nickname}: {e}")
            return [1.0, 0.72, 0, 0, 1.0, False]


def stat_finder(history, nick):
    return StatFinder.get_player_stats(history, nick)
