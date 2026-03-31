def user_theme(request):
    """
    Injecteaza tema curenta a utilizatorului in toate template-urile.
    Folosit in base.html pentru a aplica clasa corecta pe <body>.
    """
    theme = 'dark-aura'  # tema implicita
    if request.user.is_authenticated:
        try:
            theme = request.user.profile.theme
        except Exception:
            pass
    return {'current_theme': theme}