from django.urls import path
from platforma.platforma import views

urlpatterns = [
    path("", views.get_rss_feed, name="platforma_home"),
    path("update/", views.update_local, name="register_for_assignment"),
]
