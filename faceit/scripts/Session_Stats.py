import requests
import logging
import time
from faceit.scripts.headers import headers
from faceit.scripts.stat_finder import StatFinder
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Set up logging
logger = logging.getLogger(__name__)

# Configure requests with timeouts and retries
def get_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

class SessionAnalyzer:
    """Class for analyzing player session statistics"""
    
    def __init__(self, player_id, nickname, configured_time):
        """Initialize with player ID, nickname, and configured time"""
        self.player_id = player_id
        self.nickname = nickname
        self.configured_time = configured_time
        self.from_time = int(configured_time - (60 * 60 * 24))  # 24 hours before (increased from 6)
        self.to_time = int(configured_time)
        self.session = get_session()
        
        logger.info(f"Session analyzer initialized for {nickname} (ID: {player_id}) from {self.from_time} to {self.to_time}")
    
    def analyze(self):
        """Analyze the player's session stats"""
        start_time = time.time()
        
        # Try a sequence of approaches to get player history, from most general to most specific
        
        # 1. First try without specifying a game (gets all games)
        try:
            logger.info(f"Getting history without game filter for player {self.nickname}")
            parameters = {
                'from': self.from_time, 
                'to': self.to_time,
                'limit': 50  # Increased from 20
            }
            
            response = self.session.get(
                f'https://open.faceit.com/data/v4/players/{self.player_id}/history',
                params=parameters,
                headers=headers,
                timeout=15
            )
            
            history = response.json()
            
            if 'items' in history and len(history['items']) > 0:
                logger.info(f"Found {len(history['items'])} matches for player {self.nickname} without game filter")
                stats = StatFinder.get_player_stats(history, self.nickname)
                if stats[0] != 1.0 or stats[1] != 0.72:  # Check if we got non-default values
                    duration = time.time() - start_time
                    logger.info(f"Successfully generated stats for {self.nickname} in {duration:.2f}s")
                    return stats
                logger.warning(f"Default values returned, trying another approach...")
        except Exception as e:
            logger.error(f"Error getting history without game filter: {str(e)}")
        
        # 2. Try with specific game IDs
        for game_id in ['cs2', 'csgo', 'cs']:
            try:
                logger.info(f"Getting history with game={game_id} for player {self.nickname}")
                parameters = {
                    'game': game_id, 
                    'from': self.from_time, 
                    'to': self.to_time,
                    'limit': 50  # Increased from 20
                }
                
                response = self.session.get(
                    f'https://open.faceit.com/data/v4/players/{self.player_id}/history',
                    params=parameters,
                    headers=headers,
                    timeout=15
                )
                
                history = response.json()
                
                if 'items' in history and len(history['items']) > 0:
                    logger.info(f"Found {len(history['items'])} matches for player {self.nickname} with game={game_id}")
                    stats = StatFinder.get_player_stats(history, self.nickname)
                    if stats[0] != 1.0 or stats[1] != 0.72:  # Check if we got non-default values
                        duration = time.time() - start_time
                        logger.info(f"Successfully generated stats for {self.nickname} in {duration:.2f}s")
                        return stats
                    logger.warning(f"Default values returned, trying another approach...")
            except Exception as e:
                logger.error(f"Error getting history with game={game_id}: {str(e)}")
        
        # 3. Last resort - try a much longer time window (30 days)
        try:
            longer_from_time = int(self.configured_time - (60 * 60 * 24 * 30))
            logger.info(f"Trying with extended time window (30 days) for player {self.nickname}")
            parameters = {
                'from': longer_from_time, 
                'to': self.to_time,
                'limit': 100  # Try to get more matches
            }
            
            response = self.session.get(
                f'https://open.faceit.com/data/v4/players/{self.player_id}/history',
                params=parameters,
                headers=headers,
                timeout=20
            )
            
            history = response.json()
            
            if 'items' in history and len(history['items']) > 0:
                logger.info(f"Found {len(history['items'])} matches for player {self.nickname} with extended time window")
                stats = StatFinder.get_player_stats(history, self.nickname)
                if stats[0] != 1.0 or stats[1] != 0.72:  # Check if we got non-default values
                    duration = time.time() - start_time
                    logger.info(f"Successfully generated stats for {self.nickname} in {duration:.2f}s")
                    return stats
                logger.warning(f"Default values returned even with extended time window")
        except Exception as e:
            logger.error(f"Error getting history with extended time window: {str(e)}")
        
        # 4. If all else fails, but we actually found matches, try a direct match-by-match approach
        try:
            if 'items' in history and len(history['items']) > 0:
                logger.info(f"Trying direct match analysis for player {self.nickname}")
                
                # Process the first match directly
                match_id = history['items'][0]['match_id']
                logger.info(f"Analyzing match {match_id} directly")
                
                match_stats = requests.get(
                    f'https://open.faceit.com/data/v4/matches/{match_id}/stats',
                    headers=headers,
                    timeout=15
                ).json()
                
                # Look for player stats in this match
                for team in match_stats['rounds'][0]['teams']:
                    for player in team['players']:
                        if player['nickname'].lower() == self.nickname.lower():
                            logger.info(f"Found direct stats for player {self.nickname}")
                            k = float(player['player_stats']['Kills'])
                            d = float(player['player_stats']['Deaths'])
                            if d == 0:
                                d = 1
                            kd = k / d
                            kr = float(player['player_stats']['K/R Ratio'])
                            # Return some reasonable values based on the direct match
                            return [kd, kr, 1, 0, kd * 1.5]
            
        except Exception as e:
            logger.error(f"Error in direct match analysis: {str(e)}")
        
        # If no games found or all attempts failed, return default values
        duration = time.time() - start_time
        logger.warning(f"No valid stats found for player {self.nickname} after {duration:.2f}s, returning default stats")
        return [1.0, 0.72, 0, 0, 0.0]
    
    @classmethod
    def get_session_stats(cls, player_id, nickname, configured_time):
        """Class method to create an instance and run the analysis"""
        analyzer = cls(player_id, nickname, configured_time)
        return analyzer.analyze()

# For backward compatibility
def session(p_id, nick, configured_time):
    """Legacy function that uses the class method"""
    return SessionAnalyzer.get_session_stats(p_id, nick, configured_time)
