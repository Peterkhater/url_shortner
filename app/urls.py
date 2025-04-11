from django.urls import path
from .views import short , home
from django.views.decorators.csrf import csrf_exempt
urlpatterns = [
    path('short/', csrf_exempt(short)), 
    path('<str:code>/', home, name="home"),  
]