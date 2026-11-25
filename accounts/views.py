from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from drives_readiness.models import DriveApplication
from drives_readiness.services import sync_student_drive_evaluations
from skills_evidence.models import EvidenceClaim, FacultyGuidance

from .forms import (
    AdminAccountCreateForm,
    AdminAccountEditForm,
    LoginForm,
    StudentProfileForm,
    StudentSignupForm,
)
from .models import StudentProfile, UserAccount


def get_current_account(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return UserAccount.objects.filter(id=user_id, is_active=True).first()


def redirect_by_role(role):
    routes = {
        UserAccount.ROLE_STUDENT: "/student/dashboard/",
        UserAccount.ROLE_FACULTY: "/faculty/dashboard/",
        UserAccount.ROLE_PLACEMENT_CELL: "/placement/dashboard/",
        UserAccount.ROLE_RECRUITER: "/recruiter/dashboard/",
        UserAccount.ROLE_ADMIN: "/admin-panel/",
    }
    return redirect(routes.get(role, "/login/"))


def require_role(request, allowed_roles):
    account = get_current_account(request)
    if not account:
        return None, redirect("/login/")
    if account.role not in allowed_roles:
        return None, redirect_by_role(account.role)
    return account, None


def set_session_account(request, account):
    request.session["user_id"] = account.id
    request.session["role"] = account.role
    request.session["regno_or_id"] = account.regno_or_id


def login_view(request):
    existing = get_current_account(request)
    if existing:
        return redirect_by_role(existing.role)

    error = None
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ident = form.cleaned_data["regno_or_id"].strip()
        raw_pw = form.cleaned_data["password"]
        account = UserAccount.objects.filter(regno_or_id__iexact=ident).first()

        if not account or not account.check_password(raw_pw):
            error = "Invalid Regno. / ID or password."
        elif not account.is_active:
            error = "This account has been deactivated by an administrator."
        else:
            set_session_account(request, account)
            return redirect_by_role(account.role)

    return render(request, "login.html", {"form": form, "error": error})


def signup_view(request):
    existing = get_current_account(request)
    if existing:
        return redirect_by_role(existing.role)

    form = StudentSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        account = UserAccount(
            regno_or_id=form.cleaned_data["regno_or_id"].strip().upper(),
            name=form.cleaned_data["name"].strip(),
            email=form.cleaned_data["email"].strip().lower(),
            role=UserAccount.ROLE_STUDENT,
            is_active=True,
        )
        account.set_password(form.cleaned_data["password"])
        account.save()

        StudentProfile.objects.create(user=account)
        set_session_account(request, account)
        return redirect("/student/profile/?welcome=1")

    return render(request, "signup.html", {"form": form})


def logout_view(request):
    request.session.flush()
    return redirect("/login/")


def student_profile_view(request):
    account, guard = require_role(request, [UserAccount.ROLE_STUDENT])
    if guard:
        return guard

    profile, _ = StudentProfile.objects.get_or_create(user=account)
    saved = request.GET.get("saved") == "1"
    welcome = request.GET.get("welcome") == "1"

    if request.method == "POST":
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            sync_student_drive_evaluations(profile)
            return redirect("/student/profile/?saved=1")
    else:
        form = StudentProfileForm(instance=profile)

    return render(
        request,
        "student_profile.html",
        {
            "account": account,
            "profile": profile,
            "form": form,
            "saved": saved,
            "welcome": welcome,
        },
    )


def admin_panel_view(request):
    account, guard = require_role(request, [UserAccount.ROLE_ADMIN])
    if guard:
        return guard

    search_q = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip().upper()
    msg = request.GET.get("msg", "")

    if request.method == "POST":
        form = AdminAccountCreateForm(request.POST)
        if form.is_valid():
            new_user = UserAccount(
                regno_or_id=form.cleaned_data["regno_or_id"].strip().upper(),
                name=form.cleaned_data["name"].strip(),
                email=form.cleaned_data["email"].strip().lower(),
                role=form.cleaned_data["role"],
                is_active=form.cleaned_data.get("is_active", True),
            )
            new_user.set_password(form.cleaned_data["password"])
            new_user.save()
            if new_user.role == UserAccount.ROLE_STUDENT:
                StudentProfile.objects.get_or_create(user=new_user)
            return redirect(f"/admin-panel/?msg=Created+account+{new_user.regno_or_id}")
    else:
        form = AdminAccountCreateForm()

    users_qs = UserAccount.objects.all().order_by("-created_at", "regno_or_id")
    if role_filter in dict(UserAccount.ROLE_CHOICES):
        users_qs = users_qs.filter(role=role_filter)
    if search_q:
        users_qs = users_qs.filter(
            Q(regno_or_id__icontains=search_q)
            | Q(name__icontains=search_q)
            | Q(email__icontains=search_q)
        )

    return render(
        request,
        "admin_panel.html",
        {
            "account": account,
            "form": form,
            "users": users_qs,
            "search_q": search_q,
            "role_filter": role_filter,
            "role_choices": UserAccount.ROLE_CHOICES,
            "msg": msg,
        },
    )


def admin_edit_account_view(request, user_id):
    account, guard = require_role(request, [UserAccount.ROLE_ADMIN])
    if guard:
        return guard

    target = get_object_or_404(UserAccount, id=user_id)
    if request.method == "POST":
        form = AdminAccountEditForm(request.POST, instance=target)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.regno_or_id = updated.regno_or_id.strip().upper()
            updated.email = updated.email.strip().lower()
            new_pw = form.cleaned_data.get("new_password")
            if new_pw:
                updated.set_password(new_pw)
            updated.save()

            if updated.role == UserAccount.ROLE_STUDENT:
                StudentProfile.objects.get_or_create(user=updated)

            return redirect(f"/admin-panel/?msg=Updated+account+{updated.regno_or_id}")
    else:
        form = AdminAccountEditForm(instance=target)

    return render(
        request,
        "admin_edit_account.html",
        {
            "account": account,
            "target": target,
            "form": form,
        },
    )


def admin_delete_account_view(request, user_id):
    account, guard = require_role(request, [UserAccount.ROLE_ADMIN])
    if guard:
        return guard

    target = get_object_or_404(UserAccount, id=user_id)
    if target.id != account.id:
        deleted_id = target.regno_or_id
        target.delete()
        return redirect(f"/admin-panel/?msg=Deleted+account+{deleted_id}")
    return redirect("/admin-panel/?msg=Cannot+delete+active+session+account")


def admin_student_dossier_view(request, regno):
    account, guard = require_role(request, [UserAccount.ROLE_ADMIN])
    if guard:
        return guard

    student_account = get_object_or_404(
        UserAccount, regno_or_id__iexact=regno, role=UserAccount.ROLE_STUDENT
    )
    profile, _ = StudentProfile.objects.get_or_create(user=student_account)
    saved = request.GET.get("saved") == "1"

    if request.method == "POST":
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            sync_student_drive_evaluations(profile)
            return redirect(f"/admin-panel/student/{student_account.regno_or_id}/?saved=1")
    else:
        form = StudentProfileForm(instance=profile)

    claims = EvidenceClaim.objects.filter(student=profile).select_related("skill", "verified_by")
    guidance_items = FacultyGuidance.objects.filter(student=profile).select_related("skill", "faculty")
    applications = DriveApplication.objects.filter(student=profile).select_related("drive")

    return render(
        request,
        "admin_student_dossier.html",
        {
            "account": account,
            "student_account": student_account,
            "profile": profile,
            "form": form,
            "claims": claims,
            "guidance_items": guidance_items,
            "applications": applications,
            "saved": saved,
        },
    )