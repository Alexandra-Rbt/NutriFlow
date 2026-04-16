def user_theme(request):
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        return {
            'current_theme': request.user.userprofile.theme
        }
    return {
        'current_theme': 'midnight'
    }