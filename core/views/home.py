from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    if request.htmx:
        return render(request, 'core/partials/shared/greeting.html')
    return render(request, 'core/index.html')
