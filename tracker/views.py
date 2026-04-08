from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta, date
import json

from .models import UserProfile, Food, FoodLog, BodyWeight, Recipe, RecipeIngredient
from .forms import (
    RegisterForm, LoginForm, UserProfileForm, ThemeForm,
    FoodLogForm, BodyWeightForm, RecipeForm, RecipeIngredientForm, CustomFoodForm
)


# ─────────────────────────────────────────
#  HELPER — obtine sau creeaza profilul
# ─────────────────────────────────────────
def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


# ─────────────────────────────────────────
#  AUTENTIFICARE
# ─────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            get_or_create_profile(user)
            login(request, user)
            messages.success(request, f'Bine ai venit, {user.first_name}! Contul tau a fost creat.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'tracker/auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Username sau parola incorecta.')
    else:
        form = LoginForm()
    return render(request, 'tracker/auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────
@login_required
def dashboard_view(request):
    profile = get_or_create_profile(request.user)
    today   = date.today()

    # Jurnalul de azi
    logs_today = FoodLog.objects.filter(user=request.user, date=today).select_related('food')

    # Totaluri zilnice
    totals = logs_today.aggregate(
        total_kcal    = Sum('kcal'),
        total_protein = Sum('protein_g'),
        total_carbs   = Sum('carbs_g'),
        total_fat     = Sum('fat_g'),
    )
    total_kcal    = float(totals['total_kcal']    or 0)
    total_protein = float(totals['total_protein'] or 0)
    total_carbs   = float(totals['total_carbs']   or 0)
    total_fat     = float(totals['total_fat']     or 0)

    # Procentaje din obiectiv
    def pct(val, target):
        return min(round(val / target * 100) if target else 0, 100)

    # Grupe de mese
    meal_groups = {}
    for meal_key, meal_label in FoodLog.MEAL_CHOICES:
        meal_logs = logs_today.filter(meal_type=meal_key)
        if meal_logs.exists():
            meal_groups[meal_label] = meal_logs

    # Ultima greutate inregistrata
    last_weight = BodyWeight.objects.filter(user=request.user).first()

    # Grafic calorii ultmele 7 zile
    week_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_kcal = FoodLog.objects.filter(user=request.user, date=day).aggregate(
            s=Sum('kcal'))['s'] or 0
        week_data.append({'date': day.strftime('%d/%m'), 'kcal': float(day_kcal)})

    context = {
        'profile':        profile,
        'today':          today,
        'logs_today':     logs_today,
        'meal_groups':    meal_groups,
        'total_kcal':     round(total_kcal, 1),
        'total_protein':  round(total_protein, 1),
        'total_carbs':    round(total_carbs, 1),
        'total_fat':      round(total_fat, 1),
        'pct_kcal':       pct(total_kcal, profile.daily_kcal_target),
        'pct_protein':    pct(total_protein, profile.protein_target_g),
        'pct_carbs':      pct(total_carbs, profile.carbs_target_g),
        'pct_fat':        pct(total_fat, profile.fat_target_g),
        'last_weight':    last_weight,
        'week_data_json': json.dumps(week_data),
        'log_form':       FoodLogForm(initial={'date': today}),
    }
    return render(request, 'tracker/dashboard.html', context)


# ─────────────────────────────────────────
#  JURNAL ALIMENTAR
# ─────────────────────────────────────────
@login_required
def log_add(request):
    if request.method == 'POST':
        form = FoodLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.user = request.user
            log.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'kcal':    float(log.kcal),
                    'protein': float(log.protein_g),
                    'carbs':   float(log.carbs_g),
                    'fat':     float(log.fat_g),
                })
            messages.success(request, f'{log.food.name} adaugat in jurnal.')
        else:
            messages.error(request, 'Eroare la adaugare. Verifica campurile.')
    return redirect('dashboard')


@login_required
def log_delete(request, pk):
    log = get_object_or_404(FoodLog, pk=pk, user=request.user)
    food_name = log.food.name
    log.delete()
    messages.success(request, f'{food_name} sters din jurnal.')
    return redirect('dashboard')


@login_required
def journal_view(request):
    """Jurnal complet cu filtrare dupa data."""
    filter_date = request.GET.get('date', str(date.today()))
    try:
        filter_date = date.fromisoformat(filter_date)
    except ValueError:
        filter_date = date.today()

    logs = FoodLog.objects.filter(
        user=request.user, date=filter_date
    ).select_related('food').order_by('meal_type', 'created_at')

    totals = logs.aggregate(
        kcal=Sum('kcal'), protein=Sum('protein_g'),
        carbs=Sum('carbs_g'), fat=Sum('fat_g'),
    )

    return render(request, 'tracker/journal.html', {
        'logs':        logs,
        'filter_date': filter_date,
        'totals':      {k: round(float(v or 0), 1) for k, v in totals.items()},
        'form':        FoodLogForm(initial={'date': filter_date}),
    })


# ─────────────────────────────────────────
#  AJAX — calcul nutritional live
# ─────────────────────────────────────────
@login_required
def nutrition_calc(request):
    """
    Preia food_id si grams, returneaza valorile nutritionale calculate.
    Apelat din JS la schimbarea gramajului in formular.
    """
    food_id = request.GET.get('food_id')
    grams   = request.GET.get('grams', 0)
    try:
        food   = Food.objects.get(pk=food_id)
        grams  = float(grams)
        result = food.calculate_nutrition(grams)
        return JsonResponse({'success': True, **result})
    except (Food.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': 'Date invalide'})


# ─────────────────────────────────────────
#  GREUTATE CORPORALA
# ─────────────────────────────────────────
@login_required
def weight_view(request):
    if request.method == 'POST':
        form = BodyWeightForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            try:
                entry.save()
                messages.success(request, 'Greutatea a fost salvata.')
            except Exception:
                messages.error(request, 'Ai deja o intrare pentru aceasta data.')
        else:
            messages.error(request, 'Date invalide.')
        return redirect('weight')

    weights = BodyWeight.objects.filter(user=request.user)[:30]
    chart_data = [
        {'date': w.date.strftime('%d/%m'), 'kg': float(w.weight_kg)}
        for w in reversed(list(weights))
    ]
    return render(request, 'tracker/weight.html', {
        'weights':        weights,
        'form':           BodyWeightForm(initial={'date': date.today()}),
        'chart_data_json': json.dumps(chart_data),
    })


@login_required
def weight_delete(request, pk):
    entry = get_object_or_404(BodyWeight, pk=pk, user=request.user)
    entry.delete()
    messages.success(request, 'Intrare stearsa.')
    return redirect('weight')


# ─────────────────────────────────────────
#  RETETE
# ─────────────────────────────────────────
@login_required
def recipes_view(request):
    recipes = Recipe.objects.filter(user=request.user).prefetch_related('ingredients__food')
    return render(request, 'tracker/recipes.html', {'recipes': recipes})


@login_required
def recipe_create(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():
            recipe      = form.save(commit=False)
            recipe.user = request.user
            recipe.save()
            messages.success(request, f'Reteta "{recipe.name}" creata. Adauga ingrediente.')
            return redirect('recipe_edit', pk=recipe.pk)
    else:
        form = RecipeForm()
    return render(request, 'tracker/recipe_form.html', {'form': form, 'title': 'Reteta noua'})


@login_required
def recipe_edit(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES, instance=recipe)
        if form.is_valid():
            form.save()
            messages.success(request, 'Reteta actualizata.')
    else:
        form = RecipeForm(instance=recipe)

    ing_form = RecipeIngredientForm()
    return render(request, 'tracker/recipe_edit.html', {
        'recipe':   recipe,
        'form':     form,
        'ing_form': ing_form,
    })


@login_required
def recipe_add_ingredient(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    if request.method == 'POST':
        form = RecipeIngredientForm(request.POST)
        if form.is_valid():
            ing        = form.save(commit=False)
            ing.recipe = recipe
            ing.save()
            recipe.recalculate_totals()
            messages.success(request, f'{ing.food.name} adaugat.')
    return redirect('recipe_edit', pk=pk)


@login_required
def recipe_delete_ingredient(request, pk, ing_pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    ing    = get_object_or_404(RecipeIngredient, pk=ing_pk, recipe=recipe)
    ing.delete()
    recipe.recalculate_totals()
    messages.success(request, 'Ingredient sters.')
    return redirect('recipe_edit', pk=pk)


@login_required
def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    recipe.delete()
    messages.success(request, f'Reteta "{recipe.name}" stearsa.')
    return redirect('recipes')


# ─────────────────────────────────────────
#  SETARI (inclusiv schimbare tema)
# ─────────────────────────────────────────
@login_required
def settings_view(request):
    profile = get_or_create_profile(request.user)

    profile_form = UserProfileForm(instance=profile)
    theme_form   = ThemeForm(instance=profile)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_theme':
            theme_form = ThemeForm(request.POST, instance=profile)
            if theme_form.is_valid():
                theme_form.save()
                messages.success(request, 'Tema schimbata cu succes!')
                return redirect('settings')

        elif action == 'update_profile':
            profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profilul a fost actualizat.')
                return redirect('settings')

    return render(request, 'tracker/settings.html', {
        'profile':      profile,
        'profile_form': profile_form,
        'theme_form':   theme_form,
        'themes': [
            {'key': 'dark-aura',  'name': 'Dark Aura',  'desc': 'Violet pe fundal intunecat',   'preview': '#0d0d14'},
            {'key': 'fresh-mint', 'name': 'Fresh Mint', 'desc': 'Verde proaspat si luminos',    'preview': '#f0fdf4'},
            {'key': 'warm-coral', 'name': 'Warm Coral', 'desc': 'Portocaliu energic si cald',   'preview': '#fff7f5'},
            {'key': 'slate-pro',  'name': 'Slate Pro',  'desc': 'Albastru profesional si curat','preview': '#f8fafc'},
        ],
    })


# ─────────────────────────────────────────
#  AJAX — schimbare tema rapida
# ─────────────────────────────────────────
@login_required
def set_theme_ajax(request):
    if request.method == 'POST':
        data  = json.loads(request.body)
        theme = data.get('theme', 'dark-aura')
        valid = [t[0] for t in UserProfile.THEME_CHOICES]
        if theme in valid:
            profile       = get_or_create_profile(request.user)
            profile.theme = theme
            profile.save(update_fields=['theme'])
            return JsonResponse({'success': True, 'theme': theme})
    return JsonResponse({'success': False}, status=400)


# ─────────────────────────────────────────
#  ALIMENTE PERSONALIZATE
# ─────────────────────────────────────────
@login_required
def foods_view(request):
    custom_foods = Food.objects.filter(created_by=request.user, is_custom=True)
    all_foods    = Food.objects.filter(is_custom=False)
    return render(request, 'tracker/foods.html', {
        'custom_foods': custom_foods,
        'all_foods':    all_foods,
        'form':         CustomFoodForm(),
    })


@login_required
def food_create(request):
    if request.method == 'POST':
        form = CustomFoodForm(request.POST)
        if form.is_valid():
            food            = form.save(commit=False)
            food.is_custom  = True
            food.created_by = request.user
            food.save()
            messages.success(request, f'Alimentul "{food.name}" a fost adaugat.')
        else:
            messages.error(request, 'Date invalide.')
    return redirect('foods')


# ─────────────────────────────────────────
#  OPEN FOOD FACTS — cautare si import
# ─────────────────────────────────────────
@login_required
def off_search(request):
    """
    AJAX: cauta alimente in Open Food Facts dupa text.
    GET ?q=chicken&page=1
    Returneaza JSON cu lista de produse.
    """
    query = request.GET.get('q', '').strip()
    page  = int(request.GET.get('page', 1))

    if len(query) < 2:
        return JsonResponse({'results': [], 'query': query})

    from .openfoodfacts_service import search_foods
    results = search_foods(query, page=page, page_size=15)
    return JsonResponse({'results': results, 'query': query, 'page': page})


@login_required
def off_barcode(request):
    """
    AJAX: cauta un produs dupa codul de bare.
    GET ?code=3017620422003
    """
    code = request.GET.get('code', '').strip()
    if not code:
        return JsonResponse({'success': False, 'error': 'Cod lipsa'})

    from .openfoodfacts_service import get_product_by_barcode
    product = get_product_by_barcode(code)
    if not product:
        return JsonResponse({'success': False, 'error': 'Produs negasit'})

    return JsonResponse({'success': True, 'product': product})


@login_required
def off_import(request):
    """
    POST: importa un produs din OFF in baza de date locala.
    Body JSON: { off_code, name, category, kcal, protein, carbs, fat, fiber }
    """
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    data = json.loads(request.body)
    from .openfoodfacts_service import import_product_to_db
    food, created = import_product_to_db(data, user=request.user)

    return JsonResponse({
        'success': True,
        'food_id': food.pk,
        'food_name': food.name,
        'created': created,
        'kcal': float(food.kcal_per_100g),
        'protein': float(food.protein_per_100g),
        'carbs': float(food.carbs_per_100g),
        'fat': float(food.fat_per_100g),
    })


# ─────────────────────────────────────────
#  AJAX — autocomplete alimente
# ─────────────────────────────────────────
@login_required
def food_autocomplete(request):
    """
    GET ?q=pui
    Returneaza max 10 alimente care contin termenul cautat.
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    from django.db.models import Q
    foods = Food.objects.filter(
        Q(name__icontains=q)
    ).order_by('name')[:10]

    results = [
        {
            'id':       f.pk,
            'name':     f.name,
            'kcal':     float(f.kcal_per_100g),
            'protein':  float(f.protein_per_100g),
            'carbs':    float(f.carbs_per_100g),
            'fat':      float(f.fat_per_100g),
            'category': f.get_category_display(),
            'off':      bool(f.off_code),
        }
        for f in foods
    ]
    return JsonResponse({'results': results})