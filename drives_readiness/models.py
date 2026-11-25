from django.db import models
from accounts.models import StudentProfile, UserAccount
from skills_evidence.models import Skill


class PlacementDrive(models.Model):
    company_name = models.CharField(max_length=140)
    role_title = models.CharField(max_length=140)
    ctc_package = models.CharField(max_length=80, blank=True)
    job_location = models.CharField(max_length=120, blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    # Formal Eligibility Criteria (strictly separated from Readiness Score)
    min_cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    max_backlogs = models.IntegerField(default=0)
    allowed_branches = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated branches (e.g. CSE, IT, ECE). Leave blank for all.",
    )
    graduation_year = models.IntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        UserAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_drives",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} — {self.role_title}"


class DriveSkillRequirement(models.Model):
    drive = models.ForeignKey(
        PlacementDrive,
        on_delete=models.CASCADE,
        related_name="skill_requirements",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="drive_requirements",
    )
    min_level = models.PositiveSmallIntegerField(default=2)
    weight = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ("drive", "skill")
        ordering = ["skill__name"]

    def __str__(self):
        return f"{self.drive.company_name}: {self.skill.name} (Lvl {self.min_level}+)"


class RecruiterGrant(models.Model):
    recruiter = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="recruiter_grants",
    )
    drive = models.ForeignKey(
        PlacementDrive,
        on_delete=models.CASCADE,
        related_name="recruiter_grants",
    )
    cohort_branch = models.CharField(
        max_length=80,
        blank=True,
        help_text="Optional branch scope (e.g. CSE). Leave blank for all eligible branches.",
    )
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(
        UserAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_grants",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("recruiter", "drive")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recruiter.regno_or_id} -> {self.drive}"


class DriveApplication(models.Model):
    STATUS_EVALUATED = "EVALUATED"
    STATUS_APPLIED = "APPLIED"
    STATUS_SHORTLISTED = "SHORTLISTED"
    STATUS_SELECTED = "SELECTED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_EVALUATED, "Evaluated"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_SHORTLISTED, "Shortlisted"),
        (STATUS_SELECTED, "Selected"),
        (STATUS_REJECTED, "Rejected"),
    ]

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="drive_applications",
    )
    drive = models.ForeignKey(
        PlacementDrive,
        on_delete=models.CASCADE,
        related_name="applications",
    )

    # Live Eligibility Evaluation
    is_eligible = models.BooleanField(default=False)
    eligibility_reason = models.CharField(max_length=255, blank=True)

    # Live Readiness & Gap Evaluation
    readiness_score = models.PositiveSmallIntegerField(default=0)
    gap_summary = models.TextField(blank=True)

    # Application Lifecycle & Immutable Snapshot
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_EVALUATED,
    )
    applied_cgpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    applied_backlogs = models.IntegerField(null=True, blank=True)
    applied_readiness_score = models.PositiveSmallIntegerField(null=True, blank=True)
    applied_gap_summary = models.TextField(blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "drive")
        ordering = ["-readiness_score", "student__user__regno_or_id"]

    def __str__(self):
        return f"{self.student.user.regno_or_id} @ {self.drive} [{self.status}]"