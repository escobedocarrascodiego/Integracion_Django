from django.urls import path

from municipal import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("procedures/", views.ProcedureListView.as_view(), name="procedure-list"),
    path("procedures/<str:code>/", views.ProcedureDetailView.as_view(), name="procedure-detail"),
    path("complaints/", views.MyComplaintListView.as_view(), name="complaint-list"),
    path("complaints/<str:tracking_code>/", views.MyComplaintDetailView.as_view(), name="complaint-detail"),
]
