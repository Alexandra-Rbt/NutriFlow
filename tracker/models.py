from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ─────────────────────────────────────────
#  PROFIL UTILIZATOR (include tema aleasa)
# ─────────────────────────────────────────
class UserProfile(models.Model):
    THEME_CHOICES = [
        ('dark-aura',   'Dark Aura'),
        ('fresh-mint',  'Fresh Mint'),
        ('warm-coral',  'Warm Coral'),
        ('slate-pro',   'Slate Pro'),
    ]
    GENDER_CHOICES = [('M', 'Masculin'), ('F', 'Feminin'), ('O', 'Altul')]
    ACTIVITY_CHOICES = [
        ('sedentary',   'Sedentar'),
        ('light',       'Usor activ'),
        ('moderate',    'Moderat activ'),
        ('active',      'Activ'),
        ('very_active', 'Foarte activ'),
    ]
    GOAL_CHOICES = [
        ('lose',     'Slabit'),
        ('maintain', 'Mentinere'),
        ('gain',     'Masa musculara'),
    ]

    user              = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    theme             = models.CharField(max_length=20, choices=THEME_CHOICES, default='dark-aura')
    avatar            = models.ImageField(upload_to='avatars/', blank=True, null=True)
    birth_date        = models.DateField(blank=True, null=True)
    gender            = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    height_cm         = models.PositiveSmallIntegerField(blank=True, null=True)
    activity_level    = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default='moderate')
    goal              = models.CharField(max_length=10, choices=GOAL_CHOICES, default='maintain')
    daily_kcal_target = models.PositiveIntegerField(default=2000)
    protein_target_g  = models.PositiveIntegerField(default=150)
    carbs_target_g    = models.PositiveIntegerField(default=200)
    fat_target_g      = models.PositiveIntegerField(default=65)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Profil utilizator'
        verbose_name_plural = 'Profile utilizatori'

    def __str__(self):
        return f'Profil — {self.user.username} ({self.theme})'


# ─────────────────────────────────────────
#  ALIMENT (valori la 100g)
# ─────────────────────────────────────────
class Food(models.Model):
    CATEGORY_CHOICES = [
        ('protein',   'Proteine'),
        ('grain',     'Cereale & Paste'),
        ('vegetable', 'Legume'),
        ('fruit',     'Fructe'),
        ('dairy',     'Lactate'),
        ('fat',       'Grasimi & Uleiuri'),
        ('snack',     'Snacks'),
        ('drink',     'Bauturi'),
        ('other',     'Altele'),
    ]

    name             = models.CharField(max_length=200)
    category         = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    # Valori la 100g
    kcal_per_100g    = models.DecimalField(max_digits=6, decimal_places=2)
    protein_per_100g = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    carbs_per_100g   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fat_per_100g     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fiber_per_100g   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_custom        = models.BooleanField(default=False)          # aliment adaugat de utilizator
    off_code         = models.CharField(max_length=50, blank=True, db_index=True)  # cod Open Food Facts
    created_by       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Aliment'
        verbose_name_plural = 'Alimente'
        ordering            = ['name']

    def __str__(self):
        return f'{self.name} ({self.kcal_per_100g} kcal/100g)'

    def calculate_nutrition(self, grams):
        """Calculeaza valorile nutritionale pentru gramajul dat."""
        factor = float(grams) / 100.0
        return {
            'kcal':    round(float(self.kcal_per_100g)    * factor, 1),
            'protein': round(float(self.protein_per_100g) * factor, 1),
            'carbs':   round(float(self.carbs_per_100g)   * factor, 1),
            'fat':     round(float(self.fat_per_100g)      * factor, 1),
            'fiber':   round(float(self.fiber_per_100g)   * factor, 1),
        }


# ─────────────────────────────────────────
#  JURNAL ZILNIC
# ─────────────────────────────────────────
class FoodLog(models.Model):
    MEAL_CHOICES = [
        ('breakfast', 'Mic dejun'),
        ('lunch',     'Pranz'),
        ('dinner',    'Cina'),
        ('snack',     'Gustare'),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='food_logs')
    food       = models.ForeignKey(Food, on_delete=models.CASCADE)
    date       = models.DateField(default=timezone.now)
    meal_type  = models.CharField(max_length=15, choices=MEAL_CHOICES, default='lunch')
    grams      = models.DecimalField(max_digits=6, decimal_places=1)

    # Valori calculate automat la salvare (nu se editeaza manual)
    kcal       = models.DecimalField(max_digits=7, decimal_places=1, editable=False, default=0)
    protein_g  = models.DecimalField(max_digits=6, decimal_places=1, editable=False, default=0)
    carbs_g    = models.DecimalField(max_digits=6, decimal_places=1, editable=False, default=0)
    fat_g      = models.DecimalField(max_digits=6, decimal_places=1, editable=False, default=0)
    fiber_g    = models.DecimalField(max_digits=6, decimal_places=1, editable=False, default=0)

    notes      = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Intrare jurnal'
        verbose_name_plural = 'Jurnal alimentar'
        ordering            = ['-date', 'meal_type']

    def save(self, *args, **kwargs):
        # Calcul automat la fiecare salvare — se recalculeaza din gramaj + valorile alimentului
        nutrition = self.food.calculate_nutrition(self.grams)
        self.kcal      = nutrition['kcal']
        self.protein_g = nutrition['protein']
        self.carbs_g   = nutrition['carbs']
        self.fat_g     = nutrition['fat']
        self.fiber_g   = nutrition['fiber']
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} — {self.food.name} {self.grams}g ({self.date})'


# ─────────────────────────────────────────
#  GREUTATE CORPORALA
# ─────────────────────────────────────────
class BodyWeight(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weights')
    date       = models.DateField(default=timezone.now)
    weight_kg  = models.DecimalField(max_digits=5, decimal_places=2)
    notes      = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Greutate corporala'
        verbose_name_plural = 'Greutati corporale'
        ordering            = ['-date']
        unique_together     = ['user', 'date']  # o singura intrare per zi per utilizator

    def __str__(self):
        return f'{self.user.username} — {self.weight_kg}kg ({self.date})'



#  RETETE PERSONALIZATE

class Recipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    servings = models.PositiveSmallIntegerField(default=1)
    image = models.ImageField(upload_to='recipes/', blank=True, null=True)
    prep_time_minutes = models.PositiveSmallIntegerField(default=0, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    total_kcal = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    total_protein = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    total_carbs = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    total_fat = models.DecimalField(max_digits=7, decimal_places=1, default=0)

    class Meta:
        verbose_name = 'Reteta'
        verbose_name_plural = 'Retete'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} (de {self.user.username})'

    def recalculate_totals(self):
        totals = {'kcal': 0, 'protein': 0, 'carbs': 0, 'fat': 0}

        for ing in self.ingredients.select_related('food').all():
            if ing.food:
                n = ing.food.calculate_nutrition(ing.grams)
                totals['kcal'] += n['kcal']
                totals['protein'] += n['protein']
                totals['carbs'] += n['carbs']
                totals['fat'] += n['fat']

        self.total_kcal = round(totals['kcal'], 1)
        self.total_protein = round(totals['protein'], 1)
        self.total_carbs = round(totals['carbs'], 1)
        self.total_fat = round(totals['fat'], 1)
        self.save(update_fields=['total_kcal', 'total_protein', 'total_carbs', 'total_fat', 'updated_at'])

    @property
    def kcal_per_serving(self):
        return round(float(self.total_kcal) / self.servings, 1) if self.servings else 0

    @property
    def protein_per_serving(self):
        return round(float(self.total_protein) / self.servings, 1) if self.servings else 0

    @property
    def carbs_per_serving(self):
        return round(float(self.total_carbs) / self.servings, 1) if self.servings else 0

    @property
    def fat_per_serving(self):
        return round(float(self.total_fat) / self.servings, 1) if self.servings else 0


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    food = models.ForeignKey(Food, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    grams = models.DecimalField(max_digits=6, decimal_places=1)

    class Meta:
        verbose_name = 'Ingredient reteta'
        verbose_name_plural = 'Ingrediente reteta'

    def __str__(self):
        food_name = self.food.name if self.food else self.name
        return f'{food_name} {self.grams}g in {self.recipe.name}'