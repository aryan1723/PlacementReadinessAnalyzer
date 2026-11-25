from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("student/profile/", views.student_profile_view, name="student-profile"),
    path("admin-panel/", views.admin_panel_view, name="admin-panel"),
    path("admin-panel/edit/<int:user_id>/", views.admin_edit_account_view, name="admin-edit-account"),
    path("admin-panel/delete/<int:user_id>/", views.admin_delete_account_view, name="admin-delete-account"),
    path("admin-panel/student/<str:regno>/", views.admin_student_dossier_view, name="admin-student-dossier"),
]