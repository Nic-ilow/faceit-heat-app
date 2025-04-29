import os

# Headers for API requests
headers = {
    'accept': 'application/json',
    'Authorization': f'Bearer {os.getenv("FACEIT_API_KEY")}'
} 
