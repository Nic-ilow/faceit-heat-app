import requests
import logging
from faceit.scripts.headers import headers

# Set up logging
logger = logging.getLogger(__name__)

# Cache for player ELO values to reduce API calls
elo_cache = {}

class EloCalculator:
    """Class for calculating ELO discrepancies between players and teams"""
    
    @staticmethod
    def find_game_key(player_details):
        """Find the appropriate game key (cs, csgo, etc.) in player details"""
        if 'cs' in player_details['games']:
            game_key = 'cs'
        elif 'csgo' in player_details['games']:
            game_key = 'csgo'
        else:
            # Try to find any CS-related game
            game_key = None
            for key in player_details['games'].keys():
                if 'cs' in key.lower():
                    game_key = key
                    break
            
            if not game_key and player_details['games']:
                # Use the first game as fallback
                game_key = list(player_details['games'].keys())[0]
                
        return game_key
    
    @staticmethod
    def get_player_elo(player_id):
        """Get a player's ELO from the Faceit API with caching"""
        # Check if we already have this player's ELO in cache
        if player_id in elo_cache:
            logger.debug(f"Using cached ELO for player {player_id}: {elo_cache[player_id]}")
            return elo_cache[player_id]
        
        try:
            player_details = requests.get(
                f'https://open.faceit.com/data/v4/players/{player_id}',
                headers=headers
            ).json()
            
            game_key = EloCalculator.find_game_key(player_details)
            elo = float(player_details['games'][game_key]['faceit_elo'])
            
            # Cache the result
            elo_cache[player_id] = elo
            logger.debug(f"Cached ELO for player {player_id}: {elo}")
            
            return elo
        except Exception as e:
            logger.error(f"Error getting player ELO: {str(e)}")
            elo_cache[player_id] = 1500  # Cache the default value too
            return 1500  # Default ELO value
    
    @staticmethod
    def calculate_discrepancy(all_stats, player_team, player_elo):
        """Calculate the ELO discrepancy between a player and the enemy team"""
        enemy_elo = 0
        enemy_team = abs(player_team - 1)
        
        try:
            enemy_players = all_stats['rounds'][0]['teams'][enemy_team]['players']
            
            # Pre-cache all player ELOs to reduce API calls
            player_ids = [player['player_id'] for player in enemy_players]
            for player_id in player_ids:
                if player_id not in elo_cache:
                    EloCalculator.get_player_elo(player_id)
            
            # Now use the cached values
            for player in enemy_players:
                player_id = player['player_id']
                enemy_elo += elo_cache.get(player_id, 1500)
                
            enemy_avg_elo = enemy_elo / len(enemy_players)
            
            discrepancy = enemy_avg_elo - player_elo
            logger.debug(f"ELO discrepancy: {discrepancy} (Enemy: {enemy_avg_elo}, Player: {player_elo})")
            return discrepancy
            
        except Exception as e:
            logger.error(f"Error calculating ELO discrepancy: {str(e)}")
            return 0

# For backward compatibility
def elo_discrep(all_stats, p_team, p_elo):
    """Legacy function that uses the class method"""
    return EloCalculator.calculate_discrepancy(all_stats, p_team, p_elo)
