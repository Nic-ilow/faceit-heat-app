import numpy as np
import logging
import asyncio
import concurrent.futures
import time
from faceit.scripts.Lobby import LobbyAnalyzer
from faceit.scripts.Session_Stats import SessionAnalyzer

# Set up logging
logger = logging.getLogger(__name__)

class TeamAnalyzer:
    """Class for analyzing team performance data"""
    
    def __init__(self, match_id):
        """Initialize with a match ID"""
        self.match_id = match_id
        logger.info(f"TeamAnalyzer initialized for match {match_id}")
    
    async def analyze_player_async(self, player_id, nickname, configured_time):
        """Analyze a single player's stats asynchronously"""
        start_time = time.time()
        try:
            # Don't use async methods within this async method - use a direct call
            result = SessionAnalyzer.get_session_stats(player_id, nickname, configured_time)
            duration = time.time() - start_time
            logger.info(f"Player {nickname} analyzed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error analyzing player {nickname} after {duration:.2f}s: {str(e)}")
            return [1.0, 0.72, 0, 0, 0.0]  # Default stats on error
    
    def analyze(self):
        """Analyze all players in the match synchronously"""
        start_time = time.time()
        try:
            # Get player info from the lobby
            all_p_ids, all_g_ids, all_nicks, configured_time = LobbyAnalyzer.get_lobby_info(self.match_id)
            logger.info(f"Starting analysis for {len(all_nicks)} players in match {self.match_id}")
            
            # Process all players synchronously
            results = []
            for idx in range(len(all_p_ids)):
                try:
                    p_id = all_p_ids[idx]
                    nick = all_nicks[idx]
                    # Direct synchronous call, no coroutines
                    logger.info(f"Analyzing player: {nick}")
                    result = SessionAnalyzer.get_session_stats(p_id, nick, configured_time)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error analyzing player {all_nicks[idx]}: {str(e)}")
                    results.append([1.0, 0.72, 0, 0, 0.0])  # Default on error
            
            lobby_ses_dat = np.array(results)
            duration = time.time() - start_time
            logger.info(f"Completed analysis for match {self.match_id} in {duration:.2f}s")
            
            return lobby_ses_dat
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error in team analysis after {duration:.2f}s: {str(e)}")
            # Return default data on error
            dummy_data = np.array([[1.0, 0.72, 0, 0, 0.0] for _ in range(10)])
            return dummy_data
    
    @classmethod
    def get_team_info(cls, match_id):
        """Class method to create an instance and run the analysis"""
        analyzer = cls(match_id)
        
        # Simply call the analyze method directly - no asyncio needed
        try:
            return analyzer.analyze()
        except Exception as e:
            logger.error(f"Error in team analysis: {str(e)}")
            # Return empty array with right shape
            dummy_data = np.array([[1.0, 0.72, 0, 0, 0.0] for _ in range(10)])
            return dummy_data

# For backward compatibility
def team_info(match_id):
    """Legacy function that uses the class method"""
    return TeamAnalyzer.get_team_info(match_id)
