import requests
import logging
from faceit.scripts.headers import headers

# Set up logging
logger = logging.getLogger(__name__)

class LobbyAnalyzer:
    """Class for analyzing match lobbies and extracting player data"""
    
    def __init__(self, match_id):
        """Initialize with a match ID"""
        self.match_id = match_id
        logger.info(f"LobbyAnalyzer initialized for match {match_id}")
    
    def get_match_data(self):
        """Get the match data from the Faceit API"""
        try:
            response = requests.get(
                f'https://open.faceit.com/data/v4/matches/{self.match_id}',
                headers=headers
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error getting match data: {str(e)}")
            raise
    
    def analyze(self):
        """Extract player information from the match"""
        match_data = self.get_match_data()
        
        # Get configuration time
        start_time = match_data['configured_at']
        
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
        
        return all_p_ids, all_g_ids, all_nicks, start_time
    
    @classmethod
    def get_lobby_info(cls, match_id):
        """Class method to create an instance and run the analysis"""
        analyzer = cls(match_id)
        return analyzer.analyze()

# For backward compatibility
def lobby_info(match_id):
    """Legacy function that uses the class method"""
    return LobbyAnalyzer.get_lobby_info(match_id)
