from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('',         views.login_view,    name='home'),
    path('login/',   views.login_view,    name='login'),
    path('logout/',  views.logout_view,   name='logout'),
    path('register/', views.register_view, name='register'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Jurnal
    path('journal/',              views.journal_view, name='journal'),
    path('log/add/',              views.log_add,      name='log_add'),
    path('log/delete/<int:pk>/',  views.log_delete,   name='log_delete'),

    # Greutate
    path('weight/',                   views.weight_view,   name='weight'),
    path('weight/delete/<int:pk>/',   views.weight_delete, name='weight_delete'),

    # Retete
    path('recipes/',                                  views.recipes_view,            name='recipes'),
    path('recipes/create/',                           views.recipe_create,           name='recipe_create'),
    path('recipes/<int:pk>/edit/',                    views.recipe_edit,             name='recipe_edit'),
    path('recipes/<int:pk>/delete/',                  views.recipe_delete,           name='recipe_delete'),
    path('recipes/<int:pk>/ingredient/add/',          views.recipe_add_ingredient,   name='recipe_add_ingredient'),
    path('recipes/<int:pk>/ingredient/<int:ing_pk>/delete/', views.recipe_delete_ingredient, name='recipe_delete_ingredient'),

    # Alimente
    path('foods/',         views.foods_view,  name='foods'),
    path('foods/create/',  views.food_create, name='food_create'),

    # Setari
    path('settings/', views.settings_view, name='settings'),

    # AJAX
    path('api/nutrition-calc/',  views.nutrition_calc,  name='nutrition_calc'),
    path('api/set-theme/',       views.set_theme_ajax,  name='set_theme_ajax'),
]