from django.db import models
import json

# Create your models here.
class FaceitAnalysis(models.Model):
    game_id = models.CharField(max_length=100, unique=True)
    date_analyzed = models.DateTimeField(auto_now_add=True)
    match_data = models.TextField(blank=True, null=True)  # JSON data for all players
    
    def set_match_data(self, data):
        """Store match data as JSON"""
        self.match_data = json.dumps(data)
    
    def get_match_data(self):
        """Retrieve match data from JSON"""
        if self.match_data:
            return json.loads(self.match_data)
        return None
    
    def __str__(self):
        return f"Analysis for match {self.game_id}"
