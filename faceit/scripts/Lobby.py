import requests
import logging
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from faceit.scripts.headers import headers

logger = logging.getLogger(__name__)

def _get_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        backoff_jitter=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


class LobbyAnalyzer:

    def __init__(self, match_id):
        self.match_id = match_id
        self.session = _get_session()
        logger.info(f"LobbyAnalyzer initialized for match {match_id}")

    def get_match_data(self):
        try:
            response = self.session.get(
                f'https://open.faceit.com/data/v4/matches/{self.match_id}',
                headers=headers,
                timeout=15,
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error getting match data: {str(e)}")
            raise
    
    def analyze(self):
        """Extract player information from the match"""
        match_data = self.get_match_data()
        
        start_time = (
            match_data.get('configured_at')
            or match_data.get('started_at')
            or int(time.time())
        )
        logger.info(f"Match {self.match_id} start_time={start_time} (configured_at={match_data.get('configured_at')}, started_at={match_data.get('started_at')})")
        
        # Extract Team 1 players
        team_1_nicks = []
        team_1_ids = []
        team_1_game_ids = []
        
        try:
            for i in range(5):
                team_1_nicks.append(match_data['teams']['faction1']['roster'][i]['nickname'])
                team_1_game_ids.append(match_data['teams']['faction1']['roster'][i]['game_player_id'])
                team_1_ids.append(match_data['teams']['faction1']['roster'][i]['player_id'])
        except Exception as e:
            logger.error(f"Error extracting Team 1 data: {str(e)}")
        
        # Extract Team 2 players
        team_2_nicks = []
        team_2_game_ids = []
        team_2_ids = []
        
        try:
            for i in range(5):
                team_2_nicks.append(match_data['teams']['faction2']['roster'][i]['nickname'])
                team_2_game_ids.append(match_data['teams']['faction2']['roster'][i]['game_player_id'])
                team_2_ids.append(match_data['teams']['faction2']['roster'][i]['player_id'])
        except Exception as e:
            logger.error(f"Error extracting Team 2 data: {str(e)}")
        
        # Combine all player data
        all_p_ids = team_1_ids + team_2_ids
        all_g_ids = team_1_game_ids + team_2_game_ids
        all_nicks = team_1_nicks + team_2_nicks
        
        logger.info(f"Extracted {len(all_nicks)} players from match {self.match_id}")
        
        team1_name = match_data['teams']['faction1'].get('name', 'Team 1')
        team2_name = match_data['teams']['faction2'].get('name', 'Team 2')

        return all_p_ids, all_g_ids, all_nicks, start_time, team1_name, team2_name
    
    @classmethod
    def get_lobby_info(cls, match_id):
        """Class method to create an instance and run the analysis"""
        analyzer = cls(match_id)
        return analyzer.analyze()

# For backward compatibility
def lobby_info(match_id):
    """Legacy function that uses the class method"""
    return LobbyAnalyzer.get_lobby_info(match_id)
