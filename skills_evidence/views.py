from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import StudentProfile, UserAccount
from accounts.views import require_role
from drives_readiness.models import DriveApplication
from drives_readiness.services import sync_student_drive_evaluations

from .forms import (
    CLAIM_FORM_MAP,
    FacultyGuidanceForm,
    SkillForm,
    VerifyClaimForm,
)
from .models import EvidenceClaim, FacultyGuidance, Skill


def student_claims_view(request):
    account, guard = require_role(request, [UserAccount.ROLE_STUDENT])
    if guard:
        return guard

    profile, _ = StudentProfile.objects.get_or_create(user=account)
    selected_type = request.GET.get("type", "").strip().upper()
    if selected_type not in CLAIM_FORM_MAP:
        selected_type = ""

    status_filter = request.GET.get("status", "").strip().upper()
    msg = request.GET.get("msg", "")

    form = None
    if selected_type:
        FormClass = CLAIM_FORM_MAP[selected_type]
        if request.method == "POST":
            form = FormClass(request.POST, request.FILES)
            if form.is_valid():
                claim = form.save(commit=False)
                claim.student = profile
                claim.claim_type = selected_type
                claim.status = EvidenceClaim.STATUS_PENDING
                claim.verified_level = None
                claim.verified_by = None
                claim.verified_at = None
                claim.save()
                return redirect(f"/student/claims/?msg=Submitted+{selected_type}+claim+for+review")
        else:
            form = FormClass()

    claims_qs = EvidenceClaim.objects.filter(student=profile).select_related("skill", "verified_by")
    if status_filter in [
        EvidenceClaim.STATUS_PENDING,
        EvidenceClaim.STATUS_VERIFIED,
        EvidenceClaim.STATUS_DECLINED,
    ]:
        claims_qs = claims_qs.filter(status=status_filter)

    return render(
        request,
        "student_claims.html",
        {
            "account": account,
            "profile": profile,
            "claim_types": EvidenceClaim.TYPE_CHOICES,
            "selected_type": selected_type,
            "form": form,
            "claims": claims_qs,
            "status_filter": status_filter,
            "msg": msg,
        },
    )


def student_delete_claim_view(request, claim_id):
    account, guard = require_role(request, [UserAccount.ROLE_STUDENT])
    if guard:
        return guard

    profile, _ = StudentProfile.objects.get_or_create(user=account)
    claim = get_object_or_404(EvidenceClaim, id=claim_id, student=profile)
    if claim.status == EvidenceClaim.STATUS_PENDING:
        claim.delete()
        return redirect("/student/claims/?msg=Pending+claim+withdrawn")
    return redirect("/student/claims/?msg=Verified+or+declined+claims+cannot+be+deleted")


def faculty_dashboard_view(request):
    account, guard = require_role(request, [UserAccount.ROLE_FACULTY])
    if guard:
        return guard

    search_q = request.GET.get("q", "").strip()
    claim_status = request.GET.get("status", "").strip().upper()
    guidance_saved = request.GET.get("guidance_saved") == "1"

    if request.method == "POST":
        guidance_form = FacultyGuidanceForm(request.POST)
        if guidance_form.is_valid():
            guidance = guidance_form.save(commit=False)
            guidance.faculty = account
            guidance.save()
            return redirect("/faculty/dashboard/?guidance_saved=1")
    else:
        initial_student_id = request.GET.get("student_id")
        initial = {"student": initial_student_id} if initial_student_id else None
        guidance_form = FacultyGuidanceForm(initial=initial)

    students_qs = StudentProfile.objects.select_related("user").order_by("user__regno_or_id")
    if search_q:
        students_qs = students_qs.filter(
            Q(user__regno_or_id__icontains=search_q)
            | Q(user__name__icontains=search_q)
            | Q(branch__icontains=search_q)
        )

    claims_qs = EvidenceClaim.objects.select_related("student__user", "skill", "verified_by")
    if search_q:
        claims_qs = claims_qs.filter(
            Q(student__user__regno_or_id__icontains=search_q)
            | Q(student__user__name__icontains=search_q)
            | Q(title__icontains=search_q)
        )
    if claim_status in [
        EvidenceClaim.STATUS_PENDING,
        EvidenceClaim.STATUS_VERIFIED,
        EvidenceClaim.STATUS_DECLINED,
    ]:
        claims_qs = claims_qs.filter(status=claim_status)

    recent_guidance = FacultyGuidance.objects.select_related("student__user", "faculty", "skill")[:20]

    return render(
        request,
        "faculty_dashboard.html",
        {
            "account": account,
            "search_q": search_q,
            "claim_status": claim_status,
            "students": students_qs,
            "claims": claims_qs,
            "guidance_form": guidance_form,
            "recent_guidance": recent_guidance,
            "guidance_saved": guidance_saved,
        },
    )


def faculty_student_detail_view(request, regno):
    account, guard = require_role(request, [UserAccount.ROLE_FACULTY])
    if guard:
        return guard

    student_account = get_object_or_404(
        UserAccount, regno_or_id__iexact=regno, role=UserAccount.ROLE_STUDENT
    )
    profile, _ = StudentProfile.objects.get_or_create(user=student_account)

    if request.method == "POST":
        guidance_form = FacultyGuidanceForm(request.POST)
        if guidance_form.is_valid():
            guidance = guidance_form.save(commit=False)
            guidance.faculty = account
            guidance.student = profile
            guidance.save()
            return redirect(f"/faculty/student/{student_account.regno_or_id}/?saved=1")
    else:
        guidance_form = FacultyGuidanceForm(initial={"student": profile.id})

    claims = EvidenceClaim.objects.filter(student=profile).select_related("skill", "verified_by")
    guidance_items = FacultyGuidance.objects.filter(student=profile).select_related("skill", "faculty")
    applications = DriveApplication.objects.filter(student=profile).select_related("drive")

    return render(
        request,
        "faculty_student_detail.html",
        {
            "account": account,
            "student_account": student_account,
            "profile": profile,
            "claims": claims,
            "guidance_items": guidance_items,
            "applications": applications,
            "guidance_form": guidance_form,
            "saved": request.GET.get("saved") == "1",
        },
    )


def verify_claim_view(request, claim_id):
    account, guard = require_role(request, [UserAccount.ROLE_FACULTY])
    if guard:
        return guard

    claim = get_object_or_404(
        EvidenceClaim.objects.select_related("student__user", "skill"), id=claim_id
    )

    if request.method == "POST":
        form = VerifyClaimForm(request.POST, instance=claim)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.verified_by = account
            updated.verified_at = timezone.now()
            if updated.status != EvidenceClaim.STATUS_VERIFIED:
                updated.verified_level = None
            updated.save()

            # Recalculate readiness & skill gaps for this student across drives
            sync_student_drive_evaluations(claim.student)
            return redirect("/faculty/dashboard/")
    else:
        form = VerifyClaimForm(instance=claim)

    return render(
        request,
        "verify_claim.html",
        {
            "account": account,
            "claim": claim,
            "form": form,
        },
    )


def admin_skills_view(request):
    account, guard = require_role(request, [UserAccount.ROLE_ADMIN])
    if guard:
        return guard

    edit_id = request.GET.get("edit")
    delete_id = request.GET.get("delete")
    msg = request.GET.get("msg", "")

    if delete_id:
        skill_to_del = get_object_or_404(Skill, id=delete_id)
        deleted_name = skill_to_del.name
        skill_to_del.delete()
        return redirect(f"/admin-skills/?msg=Deleted+skill+{deleted_name}")

    instance = get_object_or_404(Skill, id=edit_id) if edit_id else None

    if request.method == "POST":
        form = SkillForm(request.POST, instance=instance)
        if form.is_valid():
            saved_skill = form.save()
            return redirect(f"/admin-skills/?msg=Saved+skill+{saved_skill.name}")
    else:
        form = SkillForm(instance=instance)

    skills = Skill.objects.all()
    return render(
        request,
        "admin_skills.html",
        {
            "account": account,
            "form": form,
            "instance": instance,
            "skills": skills,
            "msg": msg,
        },
    )