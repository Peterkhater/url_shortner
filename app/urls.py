from django.urls import path
from .views import short, home

urlpatterns = [
    path('<str:code>/', home, name="home"),
    path('short/',short,name="short"),
]
