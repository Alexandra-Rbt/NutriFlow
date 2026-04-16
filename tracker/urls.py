from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.dashboard_view, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Core app
    path('journal/', views.journal_view, name='journal'),
    path('weight/', views.weight_view, name='weight'),
    path('planner/', views.planner_view, name='planner'),
    path('shopping-list/', views.shopping_list_view, name='shopping_list'),
    path('shopping-list/generate/', views.generate_shopping_list_view, name='generate_shopping_list'),
    path('settings/', views.settings_view, name='settings'),

    # Recipes
    path('recipes/', views.recipes_view, name='recipes'),
    path('recipes/create/', views.recipe_create_view, name='recipe_create'),
    path('recipes/<int:pk>/', views.recipe_detail_view, name='recipe_detail'),
    path('recipes/<int:pk>/edit/', views.recipe_edit_view, name='recipe_edit'),
    path('recipes/<int:pk>/delete/', views.recipe_delete_view, name='recipe_delete'),
    path('recipes/<int:pk>/plan/', views.recipe_add_to_planner_view, name='recipe_add_to_planner'),

    # Foods
    path('foods/', views.foods_view, name='foods'),
    path('foods/create/', views.food_create_view, name='food_create'),

    # API / utility
    path('api/nutrition-calc/', views.nutrition_calc, name='nutrition_calc'),
    path('api/set-theme/', views.set_theme_ajax, name='set_theme_ajax'),
    path('api/food-autocomplete/', views.food_autocomplete, name='food_autocomplete'),
    path('api/off/search/', views.off_search, name='off_search'),
    path('api/off/barcode/', views.off_barcode, name='off_barcode'),
    path('api/off/import/', views.off_import, name='off_import'),
]