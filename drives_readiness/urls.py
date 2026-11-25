from django.urls import path
from . import views

urlpatterns = [
    path("student/dashboard/", views.student_dashboard_view, name="student-dashboard"),
    path("student/drives/<int:drive_id>/", views.student_drive_detail_view, name="student-drive-detail"),
    path("student/drives/<int:drive_id>/apply/", views.apply_drive_view, name="apply-drive"),
    path("placement/dashboard/", views.placement_dashboard_view, name="placement-dashboard"),
    path("placement/drives/<int:drive_id>/", views.placement_drive_detail_view, name="placement-drive-detail"),
    path("placement/drives/<int:drive_id>/edit/", views.placement_edit_drive_view, name="placement-edit-drive"),
    path("placement/drives/<int:drive_id>/delete/", views.placement_delete_drive_view, name="placement-delete-drive"),
    path("placement/student/<str:regno>/", views.placement_student_profile_view, name="placement-student-profile"),
    path("recruiter/dashboard/", views.recruiter_dashboard_view, name="recruiter-dashboard"),
    path("recruiter/drives/<int:drive_id>/", views.recruiter_drive_detail_view, name="recruiter-drive-detail"),
    path(
        "recruiter/drives/<int:drive_id>/student/<str:regno>/",
        views.recruiter_student_profile_view,
        name="recruiter-student-profile",
    ),
    path("admin-drives/", views.admin_drives_view, name="admin-drives"),
    path("admin-drives/edit/<int:drive_id>/", views.admin_edit_drive_view, name="admin-edit-drive"),
    path("admin-drives/delete/<int:drive_id>/", views.admin_delete_drive_view, name="admin-delete-drive"),
    path("admin-grants/delete/<int:grant_id>/", views.admin_delete_grant_view, name="admin-delete-grant"),
]