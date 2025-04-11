from django.urls import path
from .views import short, home
from django.views.decorators.csrf import csrf_exempt
urlpatterns = [
    path('<str:code>/', home, name="home"),
    # path('short/',short,name="short"),
    path('short/', csrf_exempt(short))
]
