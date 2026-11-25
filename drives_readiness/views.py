from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import StudentProfile, UserAccount
from accounts.views import require_role
from skills_evidence.models import EvidenceClaim, FacultyGuidance

from .forms import (
    DriveSkillRequirementForm,
    PlacementDriveForm,
    RecruiterGrantForm,
)
from .models import (
    DriveApplication,
    DriveSkillRequirement,
    PlacementDrive,
    RecruiterGrant,
)
from .services import (
    get_student_dimension_scores,
    sync_drive_evaluations,
    sync_student_drive_evaluations,
)


def student_dashboard_view(request):
    account, guard = require_role(request, [UserAccount.ROLE_STUDENT])
    if guard:
        return guard

    profile, _ = StudentProfile.objects.get_or_create(user=account)
    sync_student_drive_evaluations(profile)

    applications = (
        DriveApplication.objects.filter(student=profile, drive__is_active=True)
        .select_related("drive")
        .prefetch_related("drive__skill_requirements__skill")
    )
    claims = EvidenceClaim.objects.filter(student=profile).select_related("skill")
    verified_count = claims.filter(status=EvidenceClaim.STATUS_VERIFIED).count()
    pending_count = claims.filter(status=EvidenceClaim.STATUS_PENDING).count()
    guidance_items = FacultyGuidance.objects.filter(student=profile).select_related("faculty", "skill")
    dimension_scores = get_student_dimension_scores(profile)

    return render(
        request,
        "student_dashboard.html",
        {
            "account": account,
            "profile": profile,
            "applications": applications,
            "verified_count": verified_count,
            "pending_count": pending_count,
            "guidance_items": guidance_items,
            "dimension_scores": dimension_scores,
            "applied_msg": request.GET.get("applied") == "1",
        },
    )


def student_drive_detail_view(request, drive_id):
    account, guard = require_role(request, [UserAccount.ROLE_STUDENT])
    if guard:
        return guard

    profile, _ = StudentProfile.objects.get_or_create(user=account)
    drive = get_object_or_404(
        PlacementDrive.objects.prefetch_related("skill_requirements__skill"), id=drive_id
    )
    sync_student_drive_evaluations(profile)
    application = get_object_or_404(DriveApplication, student=profile, drive=drive)

    return render(
        request,
        "student_drive_detail.html",
        {
            "account": account,
            "profile": profile,
            "drive": drive,
            "application": application,
        },
    )


def apply_drive_view(request, drive_id):
    account, guard = require_role(request, [UserAccount.ROLE_STUDENT])
    if guard:
        return guard

    if request.method != "POST":
        return redirect("/student/dashboard/")

    profile, _ = StudentProfile.objects.get_or_create(user=account)
    drive = get_object_or_404(PlacementDrive, id=drive_id, is_active=True)
    sync_student_drive_evaluations(profile)

    application = get_object_or_404(DriveApplication, student=profile, drive=drive)
    if application.is_eligible and application.status == DriveApplication.STATUS_EVALUATED:
        application.status = DriveApplication.STATUS_APPLIED
        application.applied_cgpa = profile.cgpa
        application.applied_backlogs = profile.backlogs
        application.applied_readiness_score = application.readiness_score
        application.applied_gap_summary = application.gap_summary
        application.applied_at = timezone.now()
        application.save()

    return redirect("/student/dashboard/?applied=1")


def placement_dashboard_view(request):
    account, guard = require_role(request, [UserAccount.ROLE_PLACEMENT_CELL])
    if guard:
        return guard

    msg = request.GET.get("msg", "")

    if request.method == "POST":
        form = PlacementDriveForm(request.POST)
        if form.is_valid():
            drive = form.save(commit=False)
            drive.created_by = account
            drive.save()
            sync_drive_evaluations(drive)
            return redirect(f"/placement/drives/{drive.id}/?msg=Drive+created.+Add+skill+benchmarks+and+recruiters+below.")
    else:
        form = PlacementDriveForm()

    drives = PlacementDrive.objects.prefetch_related(
        "skill_requirements__skill", "recruiter_grants__recruiter", "applications"
    ).all()

    drive_rows = []
    for d in drives:
        apps = list(d.applications.all())
        eligible_count = sum(1 for a in apps if a.is_eligible)
        applied_count = sum(1 for a in apps if a.status != DriveApplication.STATUS_EVALUATED)
        drive_rows.append(
            {
                "drive": d,
                "eligible_count": eligible_count,
                "applied_count": applied_count,
                "recruiter_count": d.recruiter_grants.filter(is_active=True).count(),
            }
        )

    return render(
        request,
        "placement_dashboard.html",
        {
            "account": account,
            "form": form,
            "drive_rows": drive_rows,
            "msg": msg,
        },
    )


def placement_drive_detail_view(request, drive_id):
    account, guard = require_role(request, [UserAccount.ROLE_PLACEMENT_CELL])
    if guard:
        return guard

    drive = get_object_or_404(
        PlacementDrive.objects.prefetch_related("skill_requirements__skill", "recruiter_grants__recruiter"),
        id=drive_id,
    )
    msg = request.GET.get("msg", "")

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "add_skill":
            skill_form = DriveSkillRequirementForm(request.POST)
            grant_form = RecruiterGrantForm(drive_fixed=drive)
            if skill_form.is_valid():
                req_obj = skill_form.save(commit=False)
                DriveSkillRequirement.objects.update_or_create(
                    drive=drive,
                    skill=req_obj.skill,
                    defaults={"min_level": req_obj.min_level, "weight": req_obj.weight},
                )
                sync_drive_evaluations(drive)
                return redirect(f"/placement/drives/{drive.id}/?msg=Updated+drive+skill+benchmark")
        elif action == "remove_skill":
            req_id = request.POST.get("req_id")
            DriveSkillRequirement.objects.filter(id=req_id, drive=drive).delete()
            sync_drive_evaluations(drive)
            return redirect(f"/placement/drives/{drive.id}/?msg=Removed+skill+benchmark")
        elif action == "add_grant":
            grant_form = RecruiterGrantForm(request.POST, drive_fixed=drive)
            skill_form = DriveSkillRequirementForm()
            if grant_form.is_valid():
                g = grant_form.save(commit=False)
                RecruiterGrant.objects.update_or_create(
                    recruiter=g.recruiter,
                    drive=drive,
                    defaults={
                        "cohort_branch": g.cohort_branch,
                        "is_active": g.is_active,
                        "granted_by": account,
                    },
                )
                return redirect(f"/placement/drives/{drive.id}/?msg=Recruiter+attached+to+drive")
        elif action == "remove_grant":
            grant_id = request.POST.get("grant_id")
            RecruiterGrant.objects.filter(id=grant_id, drive=drive).delete()
            return redirect(f"/placement/drives/{drive.id}/?msg=Recruiter+grant+removed")
        elif action == "update_status":
            app_id = request.POST.get("app_id")
            new_status = request.POST.get("status")
            if new_status in dict(DriveApplication.STATUS_CHOICES):
                DriveApplication.objects.filter(id=app_id, drive=drive).update(status=new_status)
                return redirect(f"/placement/drives/{drive.id}/?msg=Applicant+status+updated")
    else:
        skill_form = DriveSkillRequirementForm()
        grant_form = RecruiterGrantForm(drive_fixed=drive)

    sync_drive_evaluations(drive)
    show_all = request.GET.get("show") == "all"
    apps_qs = DriveApplication.objects.filter(drive=drive).select_related("student__user")
    if not show_all:
        apps_qs = apps_qs.filter(is_eligible=True)

    grants = drive.recruiter_grants.select_related("recruiter").all()

    return render(
        request,
        "placement_drive_detail.html",
        {
            "account": account,
            "drive": drive,
            "skill_form": skill_form,
            "grant_form": grant_form,
            "grants": grants,
            "applications": apps_qs,
            "show_all": show_all,
            "status_choices": DriveApplication.STATUS_CHOICES,
            "msg": msg,
        },
    )


def placement_edit_drive_view(request, drive_id):
    account, guard = require_role(request, [UserAccount.ROLE_PLACEMENT_CELL])
    if guard:
        return guard

    drive = get_object_or_404(PlacementDrive, id=drive_id)
    if request.method == "POST":
        form = PlacementDriveForm(request.POST, instance=drive)
        if form.is_valid():
            updated = form.save()
            sync_drive_evaluations(updated)
            return redirect(f"/placement/drives/{updated.id}/?msg=Drive+details+updated")
    else:
        form = PlacementDriveForm(instance=drive)

    return render(
        request,
        "placement_edit_drive.html",
        {
            "account": account,
            "drive": drive,
            "form": form,
        },
    )


def placement_delete_drive_view(request, drive_id):
    account, guard = require_role(request, [UserAccount.ROLE_PLACEMENT_CELL])
    if guard:
        return guard

    drive = get_object_or_404(PlacementDrive, id=drive_id)
    title = f"{drive.company_name} - {drive.role_title}"
    drive.delete()
    return redirect(f"/placement/dashboard/?msg=Deleted+drive+{title}")


def placement_student_profile_view(request, regno):
    account, guard = require_role(request, [UserAccount.ROLE_PLACEMENT_CELL])
    if guard:
        return guard

    student_account = get_object_or_404(
        UserAccount, regno_or_id__iexact=regno, role=UserAccount.ROLE_STUDENT
    )
    profile, _ = StudentProfile.objects.get_or_create(user=student_account)
    claims = EvidenceClaim.objects.filter(student=profile).select_related("skill")
    applications = DriveApplication.objects.filter(student=profile).select_related("drive")

    return render(
        request,
        "candidate_profile.html",
        {
            "account": account,
            "student_account": student_account,
            "profile": profile,
            "claims": claims,
            "applications": applications,
            "back_url": request.GET.get("next", "/placement/dashboard/"),
        },
    )


def recruiter_dashboard_view(request):
    account, guard = require_role(request, [UserAccount.ROLE_RECRUITER])
    if guard:
        return guard

    grants = (
        RecruiterGrant.objects.filter(recruiter=account, is_active=True)
        .select_related("drive")
        .prefetch_related("drive__skill_requirements__skill", "drive__applications")
    )

    grant_rows = []
    for g in grants:
        apps = g.drive.applications.filter(is_eligible=True)
        if g.cohort_branch.strip():
            apps = apps.filter(student__branch__iexact=g.cohort_branch.strip())
        grant_rows.append(
            {
                "grant": g,
                "eligible_count": apps.count(),
                "applied_count": apps.exclude(status=DriveApplication.STATUS_EVALUATED).count(),
            }
        )

    return render(
        request,
        "recruiter_dashboard.html",
        {
            "account": account,
            "grant_rows": grant_rows,
        },
    )


def recruiter_drive_detail_view(request, drive_id):
    account, guard = require_role(request, [UserAccount.ROLE_RECRUITER])
    if guard:
        return guard

    grant = get_object_or_404(
        RecruiterGrant.objects.select_related("drive").prefetch_related("drive__skill_requirements__skill"),
        recruiter=account,
        drive_id=drive_id,
        is_active=True,
    )
    drive = grant.drive
    sync_drive_evaluations(drive)

    if request.method == "POST":
        app_id = request.POST.get("app_id")
        new_status = request.POST.get("status")
        if new_status in dict(DriveApplication.STATUS_CHOICES):
            DriveApplication.objects.filter(id=app_id, drive=drive).update(status=new_status)
            return redirect(f"/recruiter/drives/{drive.id}/?msg=Candidate+status+updated")

    apps_qs = DriveApplication.objects.filter(drive=drive, is_eligible=True).select_related("student__user")
    if grant.cohort_branch.strip():
        apps_qs = apps_qs.filter(student__branch__iexact=grant.cohort_branch.strip())

    return render(
        request,
        "recruiter_drive_detail.html",
        {
            "account": account,
            "grant": grant,
            "drive": drive,
            "applications": apps_qs,
            "status_choices": DriveApplication.STATUS_CHOICES,
            "msg": request.GET.get("msg", ""),
        },
    )


def recruiter_student_profile_view(request, drive_id, regno):
    account, guard = require_role(request, [UserAccount.ROLE_RECRUITER])
    if guard:
        return guard

    grant = get_object_or_404(
        RecruiterGrant, recruiter=account, drive_id=drive_id, is_active=True
    )
    student_account = get_object_or_404(
        UserAccount, regno_or_id__iexact=regno, role=UserAccount.ROLE_STUDENT
    )
    profile, _ = StudentProfile.objects.get_or_create(user=student_account)

    # Ensure student belongs to this recruiter's granted drive cohort
    app = get_object_or_404(DriveApplication, student=profile, drive=grant.drive, is_eligible=True)
    if grant.cohort_branch.strip() and (profile.branch or "").strip().lower() != grant.cohort_branch.strip().lower():
        return redirect(f"/recruiter/drives/{drive_id}/")

    claims = EvidenceClaim.objects.filter(
        student=profile, status=EvidenceClaim.STATUS_VERIFIED
    ).select_related("skill")
    applications = DriveApplication.objects.filter(student=profile, drive=grant.drive).select_related("drive")

    return render(
        request,
        "candidate_profile.html",
        {
            "account": account,
            "student_account": student_account,
            "profile": profile,
            "claims": claims,
            "applications": applications,
            "current_app": app,
            "back_url": f"/recruiter/drives/{drive_id}/",
        },
    )


def admin_drives_view(request):
    account, guard = require_role(request, [UserAccount.ROLE_ADMIN])
    if guard:
        return guard

    msg = request.GET.get("msg", "")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "drive":
            drive_form = PlacementDriveForm(request.POST)
            grant_form = RecruiterGrantForm()
            if drive_form.is_valid():
                drive = drive_form.save(commit=False)
                drive.created_by = account
                drive.save()
                sync_drive_evaluations(drive)
                return redirect(f"/admin-drives/?msg=Created+drive+{drive.company_name}")
        else:
            grant_form = RecruiterGrantForm(request.POST)
            drive_form = PlacementDriveForm()
            if grant_form.is_valid():
                g = grant_form.save(commit=False)
                RecruiterGrant.objects.update_or_create(
                    recruiter=g.recruiter,
                    drive=g.drive,
                    defaults={
                        "cohort_branch": g.cohort_branch,
                        "is_active": g.is_active,
                        "granted_by": account,
                    },
                )
                return redirect("/admin-drives/?msg=Recruiter+grant+saved")
    else:
        drive_form = PlacementDriveForm()
        grant_form = RecruiterGrantForm()

    drives = PlacementDrive.objects.prefetch_related("skill_requirements__skill").all()
    grants = RecruiterGrant.objects.select_related("recruiter", "drive").all()

    return render(
        request,
        "admin_drives.html",
        {
            "account": account,
            "drive_form": drive_form,
            "grant_form": grant_form,
            "drives": drives,
            "grants": grants,
            "msg": msg,
        },
    )


def admin_edit_drive_view(request, drive_id):
    account, guard = require_role(request, [UserAccount.ROLE_ADMIN])
    if guard:
        return guard

    drive = get_object_or_404(
        PlacementDrive.objects.prefetch_related("skill_requirements__skill"), id=drive_id
    )
    msg = request.GET.get("msg", "")

    if request.method == "POST":
        action = request.POST.get("action", "update_drive")
        if action == "add_skill":
            form = PlacementDriveForm(instance=drive)
            skill_form = DriveSkillRequirementForm(request.POST)
            if skill_form.is_valid():
                req_obj = skill_form.save(commit=False)
                DriveSkillRequirement.objects.update_or_create(
                    drive=drive,
                    skill=req_obj.skill,
                    defaults={"min_level": req_obj.min_level, "weight": req_obj.weight},
                )
                sync_drive_evaluations(drive)
                return redirect(f"/admin-drives/edit/{drive.id}/?msg=Added+skill+benchmark")
        elif action == "remove_skill":
            req_id = request.POST.get("req_id")
            DriveSkillRequirement.objects.filter(id=req_id, drive=drive).delete()
            sync_drive_evaluations(drive)
            return redirect(f"/admin-drives/edit/{drive.id}/?msg=Removed+skill+benchmark")
        else:
            form = PlacementDriveForm(request.POST, instance=drive)
            skill_form = DriveSkillRequirementForm()
            if form.is_valid():
                updated = form.save()
                sync_drive_evaluations(updated)
                return redirect(f"/admin-drives/?msg=Updated+drive+{updated.company_name}")
    else:
        form = PlacementDriveForm(instance=drive)
        skill_form = DriveSkillRequirementForm()

    return render(
        request,
        "admin_edit_drive.html",
        {
            "account": account,
            "drive": drive,
            "form": form,
            "skill_form": skill_form,
            "msg": msg,
        },
    )


def admin_delete_drive_view(request, drive_id):
    account, guard = require_role(request, [UserAccount.ROLE_ADMIN])
    if guard:
        return guard

    drive = get_object_or_404(PlacementDrive, id=drive_id)
    company = drive.company_name
    drive.delete()
    return redirect(f"/admin-drives/?msg=Deleted+drive+{company}")


def admin_delete_grant_view(request, grant_id):
    account, guard = require_role(request, [UserAccount.ROLE_ADMIN])
    if guard:
        return guard

    grant = get_object_or_404(RecruiterGrant, id=grant_id)
    grant.delete()
    return redirect("/admin-drives/?msg=Recruiter+grant+revoked")