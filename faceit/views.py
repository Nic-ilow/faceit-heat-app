from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from .forms import GameIDForm
from .models import FaceitAnalysis
import requests
import json
import numpy as np
import logging
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from prometheus_client import generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST

from faceit.scripts.Team import team_info
from faceit.scripts.Lobby import lobby_info

# Set up logging
logger = logging.getLogger(__name__)

def faceit_home(request):
    form = GameIDForm()
    return render(request, 'faceit/home.html', {
        'form': form,
        'debug': settings.DEBUG
    })

def analyze_game(request):
    if request.method == 'POST':
        form = GameIDForm(request.POST)
        if form.is_valid():
            match_input = form.cleaned_data['game_id']
            
            # Extract match ID from URL if a full URL was provided
            if '/' in match_input and ('faceit.com' in match_input or 'room' in match_input):
                try:
                    # Extract the last part of the URL which should be the match ID
                    match_id = match_input.strip('/').split('/')[-1]
                    logger.info(f"Extracted match ID {match_id} from URL {match_input}")
                except Exception as e:
                    logger.error(f"Failed to extract match ID from URL: {str(e)}")
                    return render(request, 'faceit/error.html', {
                        'error': 'Could not extract match ID from the provided URL. Please enter a valid Faceit match URL or ID.',
                        'match_input': match_input
                    })
            else:
                match_id = match_input
            
            # Check for reanalysis flag in the request - only allow if in debug mode or is developer
            force_reanalysis = request.POST.get('force_reanalysis', False) and (
                settings.DEBUG or 
                (request.user.is_authenticated and request.user.username == 'nick')
            )
            
            # Check if we already have this analysis
            existing_analysis = FaceitAnalysis.objects.filter(game_id=match_id).first()
            
            # If we have an existing analysis and not forcing reanalysis, use it
            if existing_analysis and not force_reanalysis:
                # Return existing analysis
                match_data = existing_analysis.get_match_data()
                if not match_data:
                    logger.error(f"Match data is None for match ID {match_id}")
                    return render(request, 'faceit/error.html', {
                        'error': 'Could not retrieve stored match data. Please try analyzing again.'
                    })
            else:
                # If we're forcing reanalysis, delete the existing analysis first
                if existing_analysis:
                    existing_analysis.delete()
                    logger.info(f"Deleted existing analysis for match ID {match_id} to force reanalysis")
                
                try:
                    # Get match data
                    from faceit.scripts.headers import headers
                    
                    logger.info(f"Starting analysis for match ID {match_id}")
                    
                    # Get player data for the match
                    try:
                        all_p_ids, all_g_ids, all_nicks, configured_time = lobby_info(match_id)
                        logger.info(f"Retrieved lobby info: {len(all_nicks)} players")
                    except Exception as e:
                        logger.error(f"Error getting lobby info: {str(e)}")
                        return render(request, 'faceit/error.html', {
                            'error': f'Error retrieving match lobby information: {str(e)}',
                            'match_id': match_id
                        })
                    
                    # Get match details
                    try:
                        match_details = requests.get(
                            f'https://open.faceit.com/data/v4/matches/{match_id}',
                            headers=headers
                        ).json()
                        logger.info(f"Retrieved match details")
                    except Exception as e:
                        logger.error(f"Error getting match details: {str(e)}")
                        return render(request, 'faceit/error.html', {
                            'error': f'Error retrieving match details: {str(e)}',
                            'match_id': match_id
                        })
                    
                    # Get the performance data for all players
                    try:
                        lobby_ses_dat = team_info(match_id)
                        logger.info(f"Retrieved team info with {len(lobby_ses_dat)} entries")
                        
                        # Add debug information about the returned data
                        default_count = 0
                        for entry in lobby_ses_dat:
                            if entry[0] == 1.0 and entry[1] == 0.72:
                                default_count += 1
                        
                        if default_count > 0:
                            logger.warning(f"WARNING: {default_count} out of {len(lobby_ses_dat)} players have default stats")
                        
                    except Exception as e:
                        logger.error(f"Error getting team info: {str(e)}")
                        return render(request, 'faceit/error.html', {
                            'error': f'Error analyzing team performance: {str(e)}',
                            'match_id': match_id
                        })
                    
                    # Organize player data
                    team1_players = []
                    team2_players = []
                    
                    try:
                        for i in range(len(all_nicks)):
                            player_data = {
                                'nickname': all_nicks[i],
                                'player_id': all_p_ids[i],
                                'kd_ratio': float(lobby_ses_dat[i][0]),
                                'kr_ratio': float(lobby_ses_dat[i][1]),
                                'match_count': int(lobby_ses_dat[i][2]),
                                'wins_count': int(lobby_ses_dat[i][3]),
                                'performance_score': float(lobby_ses_dat[i][4]),
                            }
                            
                            # Add to appropriate team
                            if i < 5:
                                team1_players.append(player_data)
                            else:
                                team2_players.append(player_data)
                                
                        logger.info(f"Organized player data: Team 1: {len(team1_players)}, Team 2: {len(team2_players)}")
                    except Exception as e:
                        logger.error(f"Error organizing player data: {str(e)}")
                        return render(request, 'faceit/error.html', {
                            'error': f'Error processing player data: {str(e)}',
                            'match_id': match_id
                        })
                    
                    # Complete match data
                    match_data = {
                        'match_id': match_id,
                        'team1': {
                            'name': match_details['teams']['faction1'].get('name', 'Team 1'),
                            'players': team1_players
                        },
                        'team2': {
                            'name': match_details['teams']['faction2'].get('name', 'Team 2'),
                            'players': team2_players
                        }
                    }
                    
                    # Save analysis to database
                    try:
                        analysis = FaceitAnalysis(game_id=match_id)
                        analysis.set_match_data(match_data)
                        analysis.save()
                        logger.info(f"Saved analysis for match ID {match_id}")
                    except Exception as e:
                        logger.error(f"Error saving analysis: {str(e)}")
                        # Continue anyway to show results
                    
                except Exception as e:
                    logger.error(f"Unexpected error in analyze_game: {str(e)}")
                    return render(request, 'faceit/error.html', {
                        'error': f'An unexpected error occurred: {str(e)}',
                        'match_id': match_id
                    })
            
            # Check that match_data is valid before rendering
            if not match_data:
                return render(request, 'faceit/error.html', {
                    'error': 'Could not generate match data. Please try a different match ID.',
                    'match_id': match_id
                })
                
            return render(request, 'faceit/results.html', {
                'match_data': match_data
            })
    
    # If not POST or form invalid, redirect to home
    return redirect('faceit:home')

def api_analyze_game(request):
    """API endpoint for game analysis"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            match_id = data.get('match_id')
            
            if not match_id:
                return JsonResponse({'error': 'Missing match_id'}, status=400)
                
            # Check if we already have this analysis
            existing_analysis = FaceitAnalysis.objects.filter(game_id=match_id).first()
            
            if existing_analysis:
                # Return existing analysis
                match_data = existing_analysis.get_match_data()
                return JsonResponse({
                    'success': True,
                    'match_data': match_data
                })
            else:
                # For implementation in the future
                return JsonResponse({
                    'success': False,
                    'error': 'Match not analyzed yet. Please use the web interface first.'
                }, status=404)
                
        except Exception as e:
            logger.error(f"API error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

def debug_match(request, match_id):
    """View for debugging match data"""
    try:
        from faceit.scripts.headers import headers
        
        # Get raw match data
        match_details = requests.get(
            f'https://open.faceit.com/data/v4/matches/{match_id}',
            headers=headers
        ).json()
        
        # Pretty print the JSON
        import json
        formatted_data = json.dumps(match_details, indent=2)
        
        debug_info = {
            'match_id': match_id,
            'data': formatted_data
        }
        
        return render(request, 'faceit/debug.html', {'debug_info': debug_info})
    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        return render(request, 'faceit/error.html', {
            'error': f'Debug error: {str(e)}'
        })

def find_player_matches(request):
    """View for finding recent matches by player nickname"""
    if request.method == 'POST':
        player_nickname = request.POST.get('player_nickname')
        if not player_nickname:
            return render(request, 'faceit/error.html', {
                'error': 'Player nickname is required'
            })
        
        try:
            from faceit.scripts.headers import headers
            
            # First, find the player's ID
            player_info = requests.get(
                f'https://open.faceit.com/data/v4/players?nickname={player_nickname}',
                headers=headers
            ).json()
            
            if 'player_id' not in player_info:
                return render(request, 'faceit/error.html', {
                    'error': f'Player not found: {player_nickname}'
                })
            
            player_id = player_info['player_id']
            logger.info(f"Found player ID: {player_id} for nickname: {player_nickname}")
            
            # Get ALL recent matches without filtering by game
            try:
                # Note: We're not specifying a game parameter, so we get ALL games
                history = requests.get(
                    f'https://open.faceit.com/data/v4/players/{player_id}/history?offset=0&limit=10',
                    headers=headers
                ).json()
                
                logger.info(f"Retrieved {len(history.get('items', []))} history items")
                
                # Process all matches
                recent_matches = []
                if 'items' in history and len(history['items']) > 0:
                    for match in history['items']:
                        # Format dates for display
                        match_date = datetime.fromtimestamp(match['started_at']).strftime('%Y-%m-%d %H:%M')
                        finished_at = 'Ongoing'
                        if match.get('finished_at'):
                            finished_at = datetime.fromtimestamp(match['finished_at']).strftime('%Y-%m-%d %H:%M')
                        
                        # Get the game type from the match data
                        game_id = match.get('game', '')
                        
                        # Hardcode the URL to always use CS2/CSGO format
                        faceit_url = f"https://www.faceit.com/en/csgo/room/{match['match_id']}"
                        
                        # For CS2 games, use CS2 in the URL
                        if game_id.lower() == 'cs2':
                            faceit_url = f"https://www.faceit.com/en/cs2/room/{match['match_id']}"
                        
                        recent_matches.append({
                            'match_id': match['match_id'],
                            'game_id': game_id,
                            'started_at': match_date,
                            'raw_started_at': match['started_at'],  # For sorting
                            'finished_at': finished_at,
                            'status': match['status'],
                            'faceit_url': faceit_url
                        })
                
                # Sort by started_at in descending order (most recent first)
                recent_matches.sort(key=lambda x: x['raw_started_at'], reverse=True)
                
                # Remove the raw_started_at key as it's no longer needed
                for match in recent_matches:
                    match.pop('raw_started_at', None)
                    
            except Exception as e:
                logger.error(f"Error getting match history: {str(e)}")
                return render(request, 'faceit/error.html', {
                    'error': f'Error getting match history: {str(e)}'
                })
            
            if not recent_matches:
                return render(request, 'faceit/error.html', {
                    'error': f'No recent matches found for player: {player_nickname}'
                })
            
            return render(request, 'faceit/player_matches.html', {
                'player_nickname': player_nickname,
                'player_id': player_id,
                'recent_matches': recent_matches,
                'offset': 10,  # For load more functionality
            })
            
        except Exception as e:
            logger.error(f"Error finding player matches: {str(e)}")
            return render(request, 'faceit/error.html', {
                'error': f'Error finding player matches: {str(e)}'
            })
    
    # GET request - show form
    return render(request, 'faceit/find_player.html')

def load_more_matches(request):
    """AJAX endpoint to load more matches for a player"""
    if request.method == 'GET':
        player_id = request.GET.get('player_id')
        offset = int(request.GET.get('offset', 0))
        
        if not player_id:
            return JsonResponse({'error': 'Player ID is required'}, status=400)
        
        try:
            from faceit.scripts.headers import headers
            from datetime import datetime
            
            # Get more player matches without filtering by game type
            history = requests.get(
                f'https://open.faceit.com/data/v4/players/{player_id}/history?offset={offset}&limit=10',
                headers=headers
            ).json()
            
            logger.info(f"Retrieved {len(history.get('items', []))} more history items with offset {offset}")
            
            more_matches = []
            if 'items' in history and len(history['items']) > 0:
                for match in history['items']:
                    # Format dates
                    match_date = datetime.fromtimestamp(match['started_at']).strftime('%Y-%m-%d %H:%M')
                    finished_at = 'Ongoing'
                    if match.get('finished_at'):
                        finished_at = datetime.fromtimestamp(match['finished_at']).strftime('%Y-%m-%d %H:%M')
                    
                    # Get game type from the match
                    game_id = match.get('game', '')
                    
                    # Hardcode the URL to always use CS2/CSGO format
                    faceit_url = f"https://www.faceit.com/en/csgo/room/{match['match_id']}"
                    
                    # For CS2 games, use CS2 in the URL
                    if game_id.lower() == 'cs2':
                        faceit_url = f"https://www.faceit.com/en/cs2/room/{match['match_id']}"
                    
                    more_matches.append({
                        'match_id': match['match_id'],
                        'game_id': game_id,
                        'started_at': match_date,
                        'raw_started_at': match['started_at'],  # For sorting
                        'finished_at': finished_at,
                        'status': match['status'],
                        'faceit_url': faceit_url
                    })
                
                # Sort by started_at in descending order (most recent first)
                more_matches.sort(key=lambda x: x['raw_started_at'], reverse=True)
                
                # Remove the raw_started_at key
                for match in more_matches:
                    match.pop('raw_started_at', None)
            
            return JsonResponse({
                'success': True,
                'matches': more_matches,
                'has_more': len(more_matches) == 10,
                'next_offset': offset + 10 if len(more_matches) == 10 else None
            })
            
        except Exception as e:
            logger.error(f"Error loading more matches: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only GET method allowed'}, status=405)

def is_dev_user(user):
    """Check if user is a developer or if we're in debug mode"""
    return settings.DEBUG or (user.is_authenticated and user.username == 'nick')

@user_passes_test(is_dev_user)
def clear_analysis_cache(request):
    """View for clearing the analysis cache - only available in debug mode or to developers"""
    if request.method == 'POST':
        match_input = request.POST.get('match_id', '')
        
        if match_input:
            # Extract match ID from URL if a full URL was provided
            if '/' in match_input and ('faceit.com' in match_input or 'room' in match_input):
                try:
                    # Extract match ID - it's always the UUID part before /scoreboard if present
                    match_id = match_input.strip('/').split('/')[-1]
                    # If the last part is 'scoreboard', use the part before it
                    if match_id == 'scoreboard':
                        match_id = match_input.strip('/').split('/')[-2]
                    logger.info(f"Extracted match ID {match_id} from URL {match_input}")
                except Exception as e:
                    logger.error(f"Failed to extract match ID from URL: {str(e)}")
                    return render(request, 'faceit/cache_cleared.html', {
                        'message': f'Error: Could not extract match ID from the provided URL.',
                        'success': False
                    })
            else:
                match_id = match_input
            
            # Clear cache for this match
            deleted, _ = FaceitAnalysis.objects.filter(game_id=match_id).delete()
            if deleted:
                logger.info(f"Cleared analysis cache for match ID {match_id}")
                return render(request, 'faceit/cache_cleared.html', {
                    'message': f'Analysis cache cleared for match ID {match_id}.',
                    'success': True
                })
            else:
                return render(request, 'faceit/cache_cleared.html', {
                    'message': f'No cached analysis found for match ID {match_id}.',
                    'success': False
                })
        else:
            # Clear all cached analyses
            deleted, _ = FaceitAnalysis.objects.all().delete()
            logger.info(f"Cleared all analysis cache ({deleted} entries)")
            return render(request, 'faceit/cache_cleared.html', {
                'message': f'All analysis cache cleared ({deleted} entries).',
                'success': True
            })
    
    # GET request - show form
    return render(request, 'faceit/clear_cache.html', {
        'debug': settings.DEBUG
    })

def metrics(request):
    registry = CollectorRegistry()
    # register any custom metrics here, e.g.:
    # from prometheus_client import Counter
    # c = Counter('faceit_requests_total','Total requests')
    # c.inc()
    output = generate_latest(registry)
    return HttpResponse(output, content_type=CONTENT_TYPE_LATEST)

