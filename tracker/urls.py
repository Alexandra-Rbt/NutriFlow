from django.urls import path
from . import views

urlpatterns = [
    path('',          views.login_view,    name='home'),
    path('login/',    views.login_view,    name='login'),
    path('logout/',   views.logout_view,   name='logout'),
    path('register/', views.register_view, name='register'),

    path('dashboard/', views.dashboard_view, name='dashboard'),

    path('journal/',             views.journal_view, name='journal'),
    path('log/add/',             views.log_add,      name='log_add'),
    path('log/delete/<int:pk>/', views.log_delete,   name='log_delete'),

    path('weight/',                  views.weight_view,   name='weight'),
    path('weight/delete/<int:pk>/',  views.weight_delete, name='weight_delete'),

    path('recipes/',                                         views.recipes_view,            name='recipes'),
    path('recipes/create/',                                  views.recipe_create,           name='recipe_create'),
    path('recipes/<int:pk>/edit/',                           views.recipe_edit,             name='recipe_edit'),
    path('recipes/<int:pk>/delete/',                         views.recipe_delete,           name='recipe_delete'),
    path('recipes/<int:pk>/ingredient/add/',                 views.recipe_add_ingredient,   name='recipe_add_ingredient'),
    path('recipes/<int:pk>/ingredient/<int:ing_pk>/delete/', views.recipe_delete_ingredient, name='recipe_delete_ingredient'),

    path('foods/',        views.foods_view,  name='foods'),
    path('foods/create/', views.food_create, name='food_create'),

    path('settings/', views.settings_view, name='settings'),

    # AJAX
    path('api/nutrition-calc/',      views.nutrition_calc,     name='nutrition_calc'),
    path('api/set-theme/',           views.set_theme_ajax,     name='set_theme_ajax'),
    path('api/food-autocomplete/',   views.food_autocomplete,  name='food_autocomplete'),

    # Open Food Facts
    path('api/off/search/',  views.off_search,  name='off_search'),
    path('api/off/barcode/', views.off_barcode, name='off_barcode'),
    path('api/off/import/',  views.off_import,  name='off_import'),
]