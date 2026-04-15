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


#  PROFIL & SETARI

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


#  JURNAL ALIMENTAR

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


#  GREUTATE
class BodyWeightForm(forms.ModelForm):
    class Meta:
        model  = BodyWeight
        fields = ['date', 'weight_kg', 'notes']
        widgets = {
            'date':      forms.DateInput(attrs={'type': 'date'}),
            'weight_kg': forms.NumberInput(attrs={'step': '0.1', 'min': '20', 'placeholder': 'ex: 75.5'}),
            'notes':     forms.TextInput(attrs={'placeholder': 'Observatii (optional)'}),
        }


#  RETETE

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = [
            'name',
            'description',
            'instructions',
            'servings',
            'prep_time_minutes',
            'image',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'nf-input',
                'placeholder': 'Ex: Bowl proteic cu pui și orez',
            }),
            'description': forms.Textarea(attrs={
                'class': 'nf-input',
                'placeholder': 'Scurtă descriere a rețetei...',
                'rows': 3,
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'nf-input',
                'placeholder': 'Scrie pașii de preparare...',
                'rows': 8,
            }),
            'servings': forms.NumberInput(attrs={
                'class': 'nf-input',
                'min': 1,
                'placeholder': '1',
            }),
            'prep_time_minutes': forms.NumberInput(attrs={
                'class': 'nf-input',
                'min': 0,
                'placeholder': 'Ex: 25',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'nf-input',
                'accept': 'image/*',
            }),
        }
        labels = {
            'name': 'Nume rețetă',
            'description': 'Descriere',
            'instructions': 'Instrucțiuni',
            'servings': 'Număr porții',
            'prep_time_minutes': 'Timp preparare (minute)',
            'image': 'Imagine',
        }

    def clean_servings(self):
        servings = self.cleaned_data.get('servings')
        if servings is not None and servings < 1:
            raise forms.ValidationError('Numărul de porții trebuie să fie cel puțin 1.')
        return servings

    def clean_prep_time_minutes(self):
        prep_time = self.cleaned_data.get('prep_time_minutes')
        if prep_time is not None and prep_time < 0:
            raise forms.ValidationError('Timpul de preparare nu poate fi negativ.')
        return prep_time


class RecipeIngredientForm(forms.ModelForm):
    class Meta:
        model = RecipeIngredient
        fields = ['name', 'grams']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'nf-input',
                'placeholder': 'Ex: Piept de pui',
            }),
            'grams': forms.NumberInput(attrs={
                'class': 'nf-input',
                'min': 0,
                'step': '0.1',
                'placeholder': 'Ex: 150',
            }),
        }
        labels = {
            'name': 'Ingredient',
            'grams': 'Grame',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Completează numele ingredientului.')
        return name

    def clean_grams(self):
        grams = self.cleaned_data.get('grams')
        if grams is None or grams <= 0:
            raise forms.ValidationError('Gramajul trebuie să fie mai mare decât 0.')
        return grams



#  ALIMENT PERSONALIZAT

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