from django.urls import path

from .views import (
	cloud_account_detail,
	cloud_account_list_create,
	cloud_instance_alerts,
	cloud_instance_detail,
	cloud_instance_list_create,
	cloud_instance_relations,
)

urlpatterns = [
	path("accounts/", cloud_account_list_create, name="cloudaccount-list-create"),
	path("accounts/<int:pk>/", cloud_account_detail, name="cloudaccount-detail"),
	path("instances/", cloud_instance_list_create, name="cloudinstance-list-create"),
	path("instances/<int:pk>/", cloud_instance_detail, name="cloudinstance-detail"),
	path("instances/<int:pk>/relations/", cloud_instance_relations, name="cloudinstance-relations"),
	path("instances/alerts/", cloud_instance_alerts, name="cloudinstance-alerts"),
]
