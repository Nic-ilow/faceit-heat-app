from django.urls import path, re_path
from django_prometheus import exports
from . import views

app_name = 'faceit'

urlpatterns = [
    path('', views.faceit_home, name='home'),
    path('analyze/', views.analyze_game, name='analyze'),
    path('api/analyze/', views.api_analyze_game, name='api_analyze'),
    path('debug/<str:match_id>/', views.debug_match, name='debug_match'),
    path('find-player/', views.find_player_matches, name='find_player'),
    path('load-more-matches/', views.load_more_matches, name='load_more_matches'),
    path('clear-cache/', views.clear_analysis_cache, name='clear_cache'),
    re_path(r'^metrics/?$', exports.ExportToDjangoView, name='metrics'),
] 
