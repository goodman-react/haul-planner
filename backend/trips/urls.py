from django.urls import path

from .views import PlanTripView

urlpatterns = [
    path("trips/", PlanTripView.as_view(), name="plan-trip"),
]
