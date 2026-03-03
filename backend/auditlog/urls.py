from django.urls import path

from .views import change_log_detail, change_log_list

urlpatterns = [
	path("change-logs/", change_log_list, name="changelog-list"),
	path("change-logs/<int:pk>/", change_log_detail, name="changelog-detail"),
]
