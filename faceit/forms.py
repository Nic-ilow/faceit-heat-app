from django import forms

class GameIDForm(forms.Form):
    game_id = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Faceit Match ID'
        })
    ) 