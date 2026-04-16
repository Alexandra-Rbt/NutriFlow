from collections import defaultdict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    RegisterForm,
    LoginForm,
    UserProfileForm,
    ThemeForm,
    FoodLogForm,
    BodyWeightForm,
    RecipeForm,
    RecipeIngredientForm,
    CustomFoodForm,
    MealPlanForm,
    ShoppingListForm,
    ShoppingListItemForm,
)
from .models import (
    UserProfile,
    Food,
    FoodLog,
    BodyWeight,
    Recipe,
    RecipeIngredient,
    MealPlan,
    ShoppingList,
    ShoppingListItem,
)
from .openfoodfacts_service import (
    search_foods as off_search_products,
    get_product_by_barcode,
)


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def get_week_range(base_date=None):
    if base_date is None:
        base_date = timezone.localdate()
    start = base_date - timedelta(days=base_date.weekday())
    end = start + timedelta(days=6)
    return start, end


def build_planner_matrix(user, start_date, end_date):
    plans = (
        MealPlan.objects
        .filter(user=user, date__range=[start_date, end_date])
        .select_related('recipe')
        .order_by('date', 'meal_type', 'created_at')
    )

    meal_order = ['breakfast', 'lunch', 'dinner', 'snack']
    days = []
    current = start_date
    while current <= end_date:
        day_items = {meal: [] for meal in meal_order}
        for item in plans:
            if item.date == current:
                day_items[item.meal_type].append(item)
        days.append({
            'date': current,
            'label': current.strftime('%A'),
            'items': day_items,
        })
        current += timedelta(days=1)
    return days


def calculate_daily_totals(user, selected_date):
    totals = (
        FoodLog.objects
        .filter(user=user, date=selected_date)
        .aggregate(
            kcal=Sum('kcal'),
            protein=Sum('protein_g'),
            carbs=Sum('carbs_g'),
            fat=Sum('fat_g'),
            fiber=Sum('fiber_g'),
        )
    )
    return {
        'kcal': float(totals['kcal'] or 0),
        'protein': float(totals['protein'] or 0),
        'carbs': float(totals['carbs'] or 0),
        'fat': float(totals['fat'] or 0),
        'fiber': float(totals['fiber'] or 0),
    }


def calculate_weekly_weight_stats(user):
    weights = BodyWeight.objects.filter(user=user).order_by('-date')[:8]
    weights = list(weights)
    latest = weights[0] if weights else None
    previous = weights[-1] if len(weights) > 1 else None
    change = None
    if latest and previous:
        change = round(float(latest.weight_kg) - float(previous.weight_kg), 2)
    return {
        'latest': latest,
        'change': change,
        'entries': weights,
    }


def aggregate_shopping_items_from_plans(user, start_date, end_date):
    plans = (
        MealPlan.objects
        .filter(user=user, date__range=[start_date, end_date])
        .select_related('recipe')
        .prefetch_related('recipe__ingredients__food')
    )

    aggregated = {}

    for plan in plans:
        multiplier = float(plan.servings or 1)

        for ingredient in plan.recipe.ingredients.all():
            item_name = ingredient.food.name if ingredient.food else ingredient.name
            key = (
                ingredient.food_id if ingredient.food_id else f'name:{item_name.strip().lower()}',
                'g'
            )

            quantity = float(ingredient.grams) * multiplier

            if key not in aggregated:
                aggregated[key] = {
                    'food': ingredient.food,
                    'name': item_name,
                    'quantity': 0,
                    'unit': 'g',
                    'source_recipe': plan.recipe,
                }

            aggregated[key]['quantity'] += quantity

    return list(aggregated.values())


def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    profile = get_or_create_profile(request.user)
    today = timezone.localdate()

    todays_logs = (
        FoodLog.objects
        .filter(user=request.user, date=today)
        .select_related('food')
        .order_by('meal_type', '-created_at')
    )
    todays_totals = calculate_daily_totals(request.user, today)
    weekly_weight = calculate_weekly_weight_stats(request.user)

    upcoming_plans = (
        MealPlan.objects
        .filter(user=request.user, date__gte=today)
        .select_related('recipe')
        .order_by('date', 'meal_type')[:6]
    )

    recent_recipes = Recipe.objects.filter(user=request.user).order_by('-created_at')[:4]

    context = {
        'profile': profile,
        'today': today,
        'todays_logs': todays_logs,
        'todays_totals': todays_totals,
        'weekly_weight': weekly_weight,
        'upcoming_plans': upcoming_plans,
        'recent_recipes': recent_recipes,
    }
    return render(request, 'tracker/dashboard.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.email = form.cleaned_data['email']
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.save()
        UserProfile.objects.get_or_create(user=user)
        messages.success(request, 'Contul a fost creat. Te poți autentifica acum.')
        return redirect('login')

    return render(request, 'tracker/auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        messages.success(request, 'Bine ai revenit.')
        return redirect('dashboard')

    return render(request, 'tracker/auth/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def journal_view(request):
    profile = get_or_create_profile(request.user)

    date_param = request.GET.get('date')
    if date_param:
        try:
            selected_date = timezone.datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    if request.method == 'POST':
        form = FoodLogForm(request.POST)
        food_id = request.POST.get('food')

        if not food_id:
            messages.error(request, 'Selectează un aliment din listă.')
        elif form.is_valid():
            try:
                food = Food.objects.get(pk=food_id)
            except Food.DoesNotExist:
                messages.error(request, 'Alimentul selectat nu există.')
            else:
                food_log = form.save(commit=False)
                food_log.user = request.user
                food_log.food = food
                food_log.date = selected_date
                food_log.save()
                messages.success(request, 'Alimentul a fost adăugat în jurnal.')
                return redirect(f'{request.path}?date={selected_date.isoformat()}')
    else:
        form = FoodLogForm()

    logs = (
        FoodLog.objects
        .filter(user=request.user, date=selected_date)
        .select_related('food')
        .order_by('meal_type', '-created_at')
    )

    grouped_logs = {
        'breakfast': [],
        'lunch': [],
        'dinner': [],
        'snack': [],
    }
    for log in logs:
        grouped_logs[log.meal_type].append(log)

    totals = calculate_daily_totals(request.user, selected_date)

    week_start, week_end = get_week_range(selected_date)
    week_days = []
    current = week_start
    while current <= week_end:
        week_days.append({
            'date': current,
            'iso': current.isoformat(),
            'day_short': current.strftime('%a'),
            'day_number': current.day,
            'active': current == selected_date,
        })
        current += timedelta(days=1)

    return render(request, 'tracker/journal.html', {
        'profile': profile,
        'form': form,
        'logs': logs,
        'grouped_logs': grouped_logs,
        'totals': totals,
        'selected_date': selected_date,
        'week_days': week_days,
    })

@login_required
def weight_view(request):
    profile = get_or_create_profile(request.user)
    form = BodyWeightForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.user = request.user
        entry.save()
        messages.success(request, 'Greutatea a fost salvată.')
        return redirect('weight')

    weights = BodyWeight.objects.filter(user=request.user).order_by('-date')
    stats = calculate_weekly_weight_stats(request.user)

    return render(request, 'tracker/weight.html', {
        'profile': profile,
        'form': form,
        'weights': weights,
        'stats': stats,
    })


@login_required
def recipes_view(request):
    profile = get_or_create_profile(request.user)
    query = request.GET.get('q', '').strip()

    recipes = Recipe.objects.filter(user=request.user).order_by('-created_at')
    if query:
        recipes = recipes.filter(name__icontains=query)

    return render(request, 'tracker/recipes.html', {
        'profile': profile,
        'recipes': recipes,
        'query': query,
    })


@login_required
def recipe_detail_view(request, pk):
    profile = get_or_create_profile(request.user)
    recipe = get_object_or_404(
        Recipe.objects.prefetch_related('ingredients__food'),
        pk=pk,
        user=request.user
    )
    planner_form = MealPlanForm(user=request.user, initial={'recipe': recipe, 'date': timezone.localdate()})

    return render(request, 'tracker/recipe_detail.html', {
        'profile': profile,
        'recipe': recipe,
        'planner_form': planner_form,
    })


@login_required
def recipe_create_view(request):
    profile = get_or_create_profile(request.user)
    recipe_form = RecipeForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and recipe_form.is_valid():
        recipe = recipe_form.save(commit=False)
        recipe.user = request.user
        recipe.save()

        ingredient_names = request.POST.getlist('ingredient_name[]')
        ingredient_grams = request.POST.getlist('ingredient_grams[]')
        ingredient_foods = request.POST.getlist('ingredient_food[]')

        for idx, name in enumerate(ingredient_names):
            name = (name or '').strip()
            grams = ingredient_grams[idx] if idx < len(ingredient_grams) else None
            food_id = ingredient_foods[idx] if idx < len(ingredient_foods) else None

            if not name or not grams:
                continue

            food = None
            if food_id:
                food = Food.objects.filter(pk=food_id).first()

            RecipeIngredient.objects.create(
                recipe=recipe,
                food=food,
                name=name,
                grams=grams,
            )

        recipe.recalculate_totals()
        messages.success(request, 'Rețeta a fost creată.')
        return redirect('recipe_detail', pk=recipe.pk)

    foods = Food.objects.all().order_by('name')

    return render(request, 'tracker/recipe_form.html', {
        'profile': profile,
        'recipe_form': recipe_form,
        'foods': foods,
        'editing': False,
    })


@login_required
def recipe_edit_view(request, pk):
    profile = get_or_create_profile(request.user)
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    recipe_form = RecipeForm(request.POST or None, request.FILES or None, instance=recipe)

    if request.method == 'POST' and recipe_form.is_valid():
        recipe = recipe_form.save()

        recipe.ingredients.all().delete()

        ingredient_names = request.POST.getlist('ingredient_name[]')
        ingredient_grams = request.POST.getlist('ingredient_grams[]')
        ingredient_foods = request.POST.getlist('ingredient_food[]')

        for idx, name in enumerate(ingredient_names):
            name = (name or '').strip()
            grams = ingredient_grams[idx] if idx < len(ingredient_grams) else None
            food_id = ingredient_foods[idx] if idx < len(ingredient_foods) else None

            if not name or not grams:
                continue

            food = None
            if food_id:
                food = Food.objects.filter(pk=food_id).first()

            RecipeIngredient.objects.create(
                recipe=recipe,
                food=food,
                name=name,
                grams=grams,
            )

        recipe.recalculate_totals()
        messages.success(request, 'Rețeta a fost actualizată.')
        return redirect('recipe_detail', pk=recipe.pk)

    foods = Food.objects.all().order_by('name')

    return render(request, 'tracker/recipe_form.html', {
        'profile': profile,
        'recipe': recipe,
        'recipe_form': recipe_form,
        'foods': foods,
        'editing': True,
    })


@login_required
def recipe_delete_view(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)

    if request.method == 'POST':
        recipe.delete()
        messages.success(request, 'Rețeta a fost ștearsă.')
        return redirect('recipes')

    return render(request, 'tracker/recipe_delete_confirm.html', {'recipe': recipe})


@login_required
def recipe_add_to_planner_view(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)

    if request.method != 'POST':
        return HttpResponseForbidden('Metodă invalidă.')

    form = MealPlanForm(request.POST, user=request.user)
    if form.is_valid():
        meal_plan = form.save(commit=False)
        meal_plan.user = request.user
        meal_plan.recipe = recipe
        meal_plan.save()
        messages.success(request, 'Rețeta a fost adăugată în planner.')
    else:
        messages.error(request, 'Nu am putut adăuga rețeta în planner.')

    return redirect('recipe_detail', pk=recipe.pk)


@login_required
def planner_view(request):
    profile = get_or_create_profile(request.user)

    week_start_param = request.GET.get('week')
    if week_start_param:
        try:
            selected_date = timezone.datetime.strptime(week_start_param, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    start_date, end_date = get_week_range(selected_date)

    form = MealPlanForm(request.POST or None, user=request.user, initial={'date': timezone.localdate()})
    if request.method == 'POST' and form.is_valid():
        meal_plan = form.save(commit=False)
        meal_plan.user = request.user
        meal_plan.save()
        messages.success(request, 'Masa a fost adăugată în planner.')
        return redirect(f"{request.path}?week={start_date}")

    week_days = build_planner_matrix(request.user, start_date, end_date)
    plans = (
        MealPlan.objects
        .filter(user=request.user, date__range=[start_date, end_date])
        .select_related('recipe')
        .order_by('date', 'meal_type')
    )

    return render(request, 'tracker/planner.html', {
        'profile': profile,
        'form': form,
        'week_days': week_days,
        'plans': plans,
        'start_date': start_date,
        'end_date': end_date,
        'prev_week': start_date - timedelta(days=7),
        'next_week': start_date + timedelta(days=7),
    })


@login_required
def shopping_list_view(request):
    profile = get_or_create_profile(request.user)
    shopping_list = (
        ShoppingList.objects
        .filter(user=request.user, is_active=True)
        .prefetch_related('items__food', 'items__source_recipe')
        .order_by('-created_at')
        .first()
    )

    list_form = ShoppingListForm(request.POST or None)
    item_form = ShoppingListItemForm(request.POST or None, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_list' and list_form.is_valid():
            ShoppingList.objects.filter(user=request.user, is_active=True).update(is_active=False)
            new_list = list_form.save(commit=False)
            new_list.user = request.user
            new_list.is_active = True
            new_list.save()
            messages.success(request, 'Lista de cumpărături a fost creată.')
            return redirect('shopping_list')

        if action == 'add_item':
            if not shopping_list:
                messages.error(request, 'Creează mai întâi o listă activă.')
                return redirect('shopping_list')

            item_form = ShoppingListItemForm(request.POST, user=request.user)
            if item_form.is_valid():
                item = item_form.save(commit=False)
                item.shopping_list = shopping_list
                item.save()
                messages.success(request, 'Produsul a fost adăugat în listă.')
                return redirect('shopping_list')

    return render(request, 'tracker/shopping_list.html', {
        'profile': profile,
        'shopping_list': shopping_list,
        'list_form': list_form,
        'item_form': item_form,
    })


@login_required
def generate_shopping_list_view(request):
    if request.method != 'POST':
        return redirect('shopping_list')

    start_date, end_date = get_week_range(timezone.localdate())
    aggregated = aggregate_shopping_items_from_plans(request.user, start_date, end_date)

    ShoppingList.objects.filter(user=request.user, is_active=True).update(is_active=False)

    shopping_list = ShoppingList.objects.create(
        user=request.user,
        name=f'Lista {start_date} - {end_date}',
        start_date=start_date,
        end_date=end_date,
        is_active=True,
    )

    for item in aggregated:
        ShoppingListItem.objects.create(
            shopping_list=shopping_list,
            food=item['food'],
            name=item['name'],
            quantity=round(item['quantity'], 1),
            unit=item['unit'],
            source_recipe=item['source_recipe'],
        )

    messages.success(request, 'Lista de cumpărături a fost generată din planner.')
    return redirect('shopping_list')


@login_required
def settings_view(request):
    profile = get_or_create_profile(request.user)

    profile_form = UserProfileForm(instance=profile)
    theme_form = ThemeForm(instance=profile)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_theme':
            theme_form = ThemeForm(request.POST, instance=profile)
            if theme_form.is_valid():
                theme_form.save()
                messages.success(request, 'Tema a fost actualizată.')
                return redirect('settings')

        elif action == 'update_profile':
            profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profilul a fost actualizat.')
                return redirect('settings')

    themes = [
        {
            'key': 'midnight',
            'name': 'Graphite Peach',
            'desc': 'Dark modern, moale și premium.',
            'top': 'linear-gradient(90deg, #e58b6b, #8ea7ff)',
            'bg': '#171b22',
            'line': '#e58b6b',
            'muted': '#2d3440',
            'block': '#1d222b',
        },
        {
            'key': 'linen',
            'name': 'Soft Sand',
            'desc': 'Light warm, editorial și aerisit.',
            'top': 'linear-gradient(90deg, #c9784a, #8b7cf6)',
            'bg': '#fdfaf6',
            'line': '#c9784a',
            'muted': '#e7ddd2',
            'block': '#fffdf9',
        },
    ]

    return render(request, 'tracker/settings.html', {
        'profile': profile,
        'profile_form': profile_form,
        'theme_form': theme_form,
        'themes': themes,
    })

@login_required
def foods_view(request):
    profile = get_or_create_profile(request.user)
    query = request.GET.get('q', '').strip()

    foods = Food.objects.all().order_by('name')
    if query:
        foods = foods.filter(name__icontains=query)

    return render(request, 'tracker/foods.html', {
        'profile': profile,
        'foods': foods,
        'query': query,
    })


@login_required
def food_create_view(request):
    profile = get_or_create_profile(request.user)
    form = CustomFoodForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        food = form.save(commit=False)
        food.created_by = request.user
        food.is_custom = True
        food.save()
        messages.success(request, 'Alimentul a fost adăugat.')
        return redirect('foods')

    return render(request, 'tracker/food_form.html', {
        'profile': profile,
        'form': form,
    })


@login_required
def nutrition_calc(request):
    food_id = request.GET.get('food_id')
    grams = request.GET.get('grams')

    if not food_id or not grams:
        return JsonResponse({'error': 'Parametri lipsă.'}, status=400)

    try:
        food = Food.objects.get(pk=food_id)
        nutrition = food.calculate_nutrition(float(grams))
        return JsonResponse(nutrition)
    except (Food.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Date invalide.'}, status=400)


@login_required
def set_theme_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    theme = request.POST.get('theme')
    profile = get_or_create_profile(request.user)

    valid_themes = [choice[0] for choice in UserProfile.THEME_CHOICES]
    if theme not in valid_themes:
        return JsonResponse({'success': False, 'error': 'Temă invalidă.'}, status=400)

    profile.theme = theme
    profile.save(update_fields=['theme', 'updated_at'])

    return JsonResponse({'success': True, 'theme': theme})


@login_required
def food_autocomplete(request):
    q = request.GET.get('q', '').strip()
    foods = Food.objects.all()

    if q:
        foods = foods.filter(name__icontains=q)

    results = [
        {
            'id': food.id,
            'name': food.name,
            'category': food.category,
            'kcal_per_100g': float(food.kcal_per_100g),
        }
        for food in foods[:12]
    ]

    return JsonResponse({'results': results})


@login_required
def off_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    results = off_search_products(query)
    return JsonResponse({'results': results})


@login_required
def off_barcode(request):
    barcode = request.GET.get('barcode', '').strip()
    if not barcode:
        return JsonResponse({'product': None}, status=400)

    product = get_product_by_barcode(barcode)
    return JsonResponse({'product': product})


@login_required
def off_import(request):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    name = request.POST.get('name', '').strip()
    category = request.POST.get('category', 'other')
    kcal = request.POST.get('kcal_per_100g', 0)
    protein = request.POST.get('protein_per_100g', 0)
    carbs = request.POST.get('carbs_per_100g', 0)
    fat = request.POST.get('fat_per_100g', 0)
    fiber = request.POST.get('fiber_per_100g', 0)
    off_code = request.POST.get('off_code', '').strip()

    if not name:
        return JsonResponse({'success': False, 'error': 'Numele lipsește.'}, status=400)

    food = Food.objects.create(
        name=name,
        category=category,
        kcal_per_100g=kcal or 0,
        protein_per_100g=protein or 0,
        carbs_per_100g=carbs or 0,
        fat_per_100g=fat or 0,
        fiber_per_100g=fiber or 0,
        off_code=off_code,
        is_custom=True,
        created_by=request.user,
    )

    return JsonResponse({
        'success': True,
        'food': {
            'id': food.id,
            'name': food.name,
        }
    })