from django.urls import path

from platforma.platforma import views

urlpatterns = [
    path("", views.get_rss_feed, name="platforma_home"),
    path("update/", views.update_local_endpoint, name="register_for_assignment"),
    path("combined/", views.get_combined_rss_feed, name="combined_feed"),
    path(
        "remove_episode/<str:episode_id>/", views.remove_episode, name="remove_episode"
    ),
]
