from django.shortcuts import render

def index(request):
    if request.htmx:
        return render(request, 'core/partials/greeting.html')
    return render(request, 'core/index.html')