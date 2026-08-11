import numpy as np
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from faceit.scripts.Lobby import LobbyAnalyzer
from faceit.scripts.Session_Stats import SessionAnalyzer

logger = logging.getLogger(__name__)

DEFAULT_STATS = [1.0, 0.72, 0, 0, 0.0, False]

class TeamAnalyzer:

    def __init__(self, match_id):
        self.match_id = match_id

    def analyze(self):
        start_time = time.time()
        try:
            all_p_ids, all_g_ids, all_nicks, configured_time, team1_name, team2_name = (
                LobbyAnalyzer.get_lobby_info(self.match_id)
            )
            logger.info(f"Starting parallel analysis for {len(all_nicks)} players in match {self.match_id}")

            results = [None] * len(all_p_ids)

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for i, (p_id, nick) in enumerate(zip(all_p_ids, all_nicks)):
                    future = executor.submit(
                        SessionAnalyzer.get_session_stats, p_id, nick, configured_time
                    )
                    futures[future] = (i, nick)

                for future in as_completed(futures):
                    idx, nick = futures[future]
                    try:
                        results[idx] = future.result()
                    except Exception as e:
                        logger.error(f"Error analyzing player {nick}: {e}")
                        results[idx] = list(DEFAULT_STATS)

            lobby_ses_dat = np.array(results)
            duration = time.time() - start_time
            logger.info(f"Completed analysis for match {self.match_id} in {duration:.2f}s")

            return lobby_ses_dat, all_p_ids, all_nicks, team1_name, team2_name

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error in team analysis after {duration:.2f}s: {e}")
            dummy_data = np.array([list(DEFAULT_STATS) for _ in range(10)])
            return dummy_data, [], [], 'Team 1', 'Team 2'

    @classmethod
    def get_team_info(cls, match_id):
        analyzer = cls(match_id)
        try:
            return analyzer.analyze()
        except Exception as e:
            logger.error(f"Error in team analysis: {e}")
            dummy_data = np.array([list(DEFAULT_STATS) for _ in range(10)])
            return dummy_data, [], [], 'Team 1', 'Team 2'


def team_info(match_id):
    return TeamAnalyzer.get_team_info(match_id)
