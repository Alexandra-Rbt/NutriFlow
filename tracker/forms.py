from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile, FoodLog, BodyWeight, Recipe, RecipeIngredient, Food



#  AUTENTIFICARE
class RegisterForm(UserCreationForm):
    email      = forms.EmailField(required=True, label='Email')
    first_name = forms.CharField(max_length=50, required=True, label='Prenume')
    last_name  = forms.CharField(max_length=50, required=True, label='Nume')

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class LoginForm(AuthenticationForm):
    pass


# ─────────────────────────────────────────
#  PROFIL & SETARI
# ─────────────────────────────────────────
class UserProfileForm(forms.ModelForm):
    class Meta:
        model  = UserProfile
        fields = [
            'avatar', 'birth_date', 'gender', 'height_cm',
            'activity_level', 'goal',
            'daily_kcal_target', 'protein_target_g', 'carbs_target_g', 'fat_target_g',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ThemeForm(forms.ModelForm):
    """Form simplu doar pentru schimbarea temei."""
    class Meta:
        model  = UserProfile
        fields = ['theme']


# ─────────────────────────────────────────
#  JURNAL ALIMENTAR
# ─────────────────────────────────────────
class FoodLogForm(forms.ModelForm):
    class Meta:
        model  = FoodLog
        fields = ['food', 'date', 'meal_type', 'grams', 'notes']
        widgets = {
            'date':  forms.DateInput(attrs={'type': 'date'}),
            'grams': forms.NumberInput(attrs={
                'step': '1',
                'min':  '1',
                'placeholder': 'ex: 150',
            }),
            'notes': forms.TextInput(attrs={'placeholder': 'Observatii (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sorteaza alimentele alfabetic
        self.fields['food'].queryset = Food.objects.all().order_by('name')
        self.fields['food'].empty_label = '— Alege aliment —'


# ─────────────────────────────────────────
#  GREUTATE
# ─────────────────────────────────────────
class BodyWeightForm(forms.ModelForm):
    class Meta:
        model  = BodyWeight
        fields = ['date', 'weight_kg', 'notes']
        widgets = {
            'date':      forms.DateInput(attrs={'type': 'date'}),
            'weight_kg': forms.NumberInput(attrs={'step': '0.1', 'min': '20', 'placeholder': 'ex: 75.5'}),
            'notes':     forms.TextInput(attrs={'placeholder': 'Observatii (optional)'}),
        }


# ─────────────────────────────────────────
#  RETETE
# ─────────────────────────────────────────
class RecipeForm(forms.ModelForm):
    class Meta:
        model  = Recipe
        fields = ['name', 'description', 'servings', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class RecipeIngredientForm(forms.ModelForm):
    class Meta:
        model  = RecipeIngredient
        fields = ['food', 'grams']
        widgets = {
            'grams': forms.NumberInput(attrs={'step': '1', 'min': '1', 'placeholder': 'grame'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['food'].queryset    = Food.objects.all().order_by('name')
        self.fields['food'].empty_label = '— Alege ingredient —'


# ─────────────────────────────────────────
#  ALIMENT PERSONALIZAT
# ─────────────────────────────────────────
class CustomFoodForm(forms.ModelForm):
    class Meta:
        model  = Food
        fields = ['name', 'category', 'kcal_per_100g', 'protein_per_100g', 'carbs_per_100g', 'fat_per_100g', 'fiber_per_100g']
        widgets = {
            'kcal_per_100g':    forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'protein_per_100g': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'carbs_per_100g':   forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'fat_per_100g':     forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'fiber_per_100g':   forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
        }