from django.urls import path
from . import views

urlpatterns = [
    path("helpdesk/", views.helpdesk_view, name="helpdesk"),
    path("helpdesk/<str:ticket_code>/", views.ticket_detail_view, name="ticket-detail"),
]