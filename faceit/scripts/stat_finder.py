import requests
import logging
import numpy as np
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from faceit.scripts.headers import headers
from faceit.scripts.Elo_Discrep import EloCalculator
from faceit.scripts.Performance_Calc import PerformanceCalculator

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

class StatFinder:
    """Class for finding and analyzing player statistics"""
    
    def __init__(self, history, nickname):
        """Initialize with player history and nickname"""
        self.history = history
        self.nickname = nickname
        # Limit to max 10 matches to prevent excessive processing
        self.match_count = min(10, len(history.get('items', [])))
        self.num_wins = 0
        self.tot_k = 0
        self.tot_d = 0
        self.tot_kr = 0
        self.perf_scores = []
        self.player_team = 0
        self.player_elo = 0
        self.session = get_session()
        
        logger.info(f"StatFinder initialized for {nickname} with {self.match_count} matches (limited from {len(history.get('items', []))})")
    
    def process_match(self, match_num):
        """Process a single match synchronously"""
        start_time = time.time()
        try:
            match_item = self.history['items'][match_num]
            match_id = match_item['match_id']
            logger.info(f"Processing match {match_id} for player {self.nickname}")
            
            # Use session with timeout
            response = self.session.get(
                f'https://open.faceit.com/data/v4/matches/{match_id}/stats',
                headers=headers,
                timeout=10  # 10 second timeout
            )
            all_stats = response.json()
            
            # Determine which team the player is on
            team1_id = match_item.get('teams', {}).get('faction1', {}).get('team_id', '')
            
            # Handle the case where the team structure might be different
            if not team1_id and 'rounds' in all_stats and len(all_stats['rounds']) > 0:
                # Just try both teams
                teams = [0, 1]
            else:
                # Try to match the team IDs
                teams = [0, 1] if all_stats['rounds'][0]['teams'][0]['team_id'] == team1_id else [1, 0]
            
            k, d, kr, kd = 0, 0, 0, 0
            player_found = False
            
            for team in teams:
                for player in all_stats['rounds'][0]['teams'][team]['players']:
                    if self.nickname.lower() == player['nickname'].lower():
                        player_found = True
                        # Get player stats
                        player_stats = player.get('player_stats', {})
                        k = float(player_stats.get('Kills', 0))
                        d = float(player_stats.get('Deaths', 1))  # Default to 1 to avoid division by zero
                        if d == 0:
                            d = 1
                        kd = k / d
                        kr = float(player_stats.get('K/R Ratio', 0))
                        self.player_team = int(team)
                        
                        # Get team win status
                        team_stats = all_stats['rounds'][0]['teams'][team].get('team_stats', {})
                        self.num_wins += int(team_stats.get('Team Win', 0))
                        
                        # Get player ELO for the first match
                        if match_num == 0:
                            player_id = player['player_id']
                            self.player_elo = EloCalculator.get_player_elo(player_id)
            
            if player_found:
                # Calculate ELO discrepancy
                discrep = EloCalculator.calculate_discrepancy(all_stats, self.player_team, self.player_elo)
                
                # Update totals
                self.tot_k += k
                self.tot_d += d
                self.tot_kr += kr
                
                # Calculate performance score
                perf_score = PerformanceCalculator.calculate(kd, kr, discrep)
                self.perf_scores.append(perf_score)
                
                duration = time.time() - start_time
                logger.info(f"Match {match_id} processed in {duration:.2f}s with KD: {kd}, KR: {kr}, Perf: {perf_score}")
                return True
            else:
                logger.warning(f"Player {self.nickname} not found in match {match_id}")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error processing match {match_num} after {duration:.2f}s: {str(e)}")
            return False
    
    def analyze(self):
        """Analyze matches synchronously"""
        start_time = time.time()
        
        if self.match_count == 0:
            logger.warning(f"No matches found for player {self.nickname}")
            return [1.0, 0.72, 0, 0, 0.0]
        
        # Process matches synchronously
        # Process up to 10 most recent matches for better stats
        max_matches = min(10, self.match_count)
        logger.info(f"Analyzing {max_matches} most recent matches for {self.nickname}")
        
        # Process each match
        success_count = 0
        for i in range(max_matches):
            try:
                if self.process_match(i):
                    success_count += 1
                
                # Break early if we have enough successful matches
                if success_count >= 3:
                    logger.info(f"Got enough successful matches ({success_count}), stopping early")
                    break
            except Exception as e:
                logger.error(f"Error in match processing: {str(e)}")
        
        # Calculate final stats
        if self.tot_d == 0:
            self.tot_d = 1
            
        if len(self.perf_scores) == 0:
            logger.warning(f"No valid matches processed for {self.nickname}, returning default stats")
            return [1.0, 0.72, 0, 0, 1.0]
        
        tot_kd = self.tot_k / self.tot_d
        tot_kr = self.tot_kr / max(1, len(self.perf_scores))
        avg_perf_score = float(np.mean(self.perf_scores))
        
        duration = time.time() - start_time
        logger.info(f"Final stats for {self.nickname} generated in {duration:.2f}s: KD: {tot_kd}, KR: {tot_kr}, " +
                   f"Matches: {len(self.perf_scores)}/{max_matches}, Wins: {self.num_wins}, Performance: {avg_perf_score}")
                   
        return [tot_kd, tot_kr, len(self.perf_scores), self.num_wins, avg_perf_score]
    
    @classmethod
    def get_player_stats(cls, history, nickname):
        """Class method to create an instance and run the analysis"""
        try:
            finder = cls(history, nickname)
            return finder.analyze()
        except Exception as e:
            logger.error(f"Error in get_player_stats for {nickname}: {str(e)}")
            return [1.0, 0.72, 0, 0, 1.0]  # Default on error

# For backward compatibility
def stat_finder(history, nick):
    """Legacy function that uses the class method"""
    return StatFinder.get_player_stats(history, nick)
