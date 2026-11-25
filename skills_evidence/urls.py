from django.urls import path
from . import views

urlpatterns = [
    path("student/claims/", views.student_claims_view, name="student-claims"),
    path("student/claims/delete/<int:claim_id>/", views.student_delete_claim_view, name="student-delete-claim"),
    path("faculty/dashboard/", views.faculty_dashboard_view, name="faculty-dashboard"),
    path("faculty/student/<str:regno>/", views.faculty_student_detail_view, name="faculty-student-detail"),
    path("faculty/verify/<int:claim_id>/", views.verify_claim_view, name="verify-claim"),
    path("admin-skills/", views.admin_skills_view, name="admin-skills"),
]