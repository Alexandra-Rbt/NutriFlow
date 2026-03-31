from django.contrib import admin
from .models import UserProfile, Food, FoodLog, BodyWeight, Recipe, RecipeIngredient


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'theme', 'daily_kcal_target', 'goal']
    list_filter   = ['theme', 'goal']


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display  = ['name', 'category', 'kcal_per_100g', 'protein_per_100g', 'carbs_per_100g', 'fat_per_100g']
    list_filter   = ['category', 'is_custom']
    search_fields = ['name']


@admin.register(FoodLog)
class FoodLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'food', 'grams', 'kcal', 'date', 'meal_type']
    list_filter  = ['meal_type', 'date']


@admin.register(BodyWeight)
class BodyWeightAdmin(admin.ModelAdmin):
    list_display = ['user', 'weight_kg', 'date']


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'servings', 'total_kcal']


admin.site.register(RecipeIngredient)