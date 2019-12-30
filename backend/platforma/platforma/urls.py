from django.urls import path
from platforma.platforma import views

urlpatterns = [
    path("", views.home, name="platforma_home"),
    path("register/", views.register_for_assignment, name="register_for_assignment"),
    path("make_cycle/", views.trigger_create_cycle, name="make_cycle"),
]
