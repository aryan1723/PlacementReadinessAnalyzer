from django.db import models
from accounts.models import StudentProfile, UserAccount


class Skill(models.Model):
    DIMENSION_TECHNICAL = "TECHNICAL"
    DIMENSION_APTITUDE = "APTITUDE"
    DIMENSION_COMMUNICATION = "COMMUNICATION"
    DIMENSION_PROJECT_DEPTH = "PROJECT_DEPTH"

    DIMENSION_CHOICES = [
        (DIMENSION_TECHNICAL, "Technical"),
        (DIMENSION_APTITUDE, "Aptitude"),
        (DIMENSION_COMMUNICATION, "Communication"),
        (DIMENSION_PROJECT_DEPTH, "Project Depth"),
    ]

    name = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=80, blank=True)
    dimension = models.CharField(
        max_length=30,
        choices=DIMENSION_CHOICES,
        default=DIMENSION_TECHNICAL,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_dimension_display()})"


class EvidenceClaim(models.Model):
    TYPE_CERTIFICATION = "CERTIFICATION"
    TYPE_PROJECT = "PROJECT"
    TYPE_ACADEMIC = "ACADEMIC"
    TYPE_INTERNSHIP = "INTERNSHIP"
    TYPE_ASSESSMENT = "ASSESSMENT"

    TYPE_CHOICES = [
        (TYPE_CERTIFICATION, "Certification"),
        (TYPE_PROJECT, "Project"),
        (TYPE_ACADEMIC, "Academic Proof"),
        (TYPE_INTERNSHIP, "Internship / Experience"),
        (TYPE_ASSESSMENT, "Assessment / Hackathon"),
    ]

    STATUS_PENDING = "PENDING"
    STATUS_VERIFIED = "VERIFIED"
    STATUS_DECLINED = "DECLINED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Review"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_DECLINED, "Declined"),
    ]

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="claims",
    )
    claim_type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claims",
    )

    # Shared fields
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    proof_link = models.URLField(blank=True)
    proof_attachment = models.FileField(upload_to="proofs/", blank=True, null=True)

    # Project & Internship fields
    project_role = models.CharField(max_length=120, blank=True)
    tech_stack = models.CharField(max_length=200, blank=True)

    # Certification & Internship organization / timeline fields
    organization = models.CharField(max_length=160, blank=True)
    credential_id = models.CharField(max_length=120, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    duration_weeks = models.PositiveIntegerField(null=True, blank=True)
    duration_hours = models.PositiveIntegerField(null=True, blank=True)
    certificate_document = models.FileField(upload_to="certificates/", blank=True, null=True)

    # Academic & Assessment score fields
    academic_result = models.CharField(max_length=120, blank=True)
    academic_grade = models.CharField(max_length=40, blank=True)
    score_text = models.CharField(max_length=80, blank=True)

    # Faculty Verification Outcome
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    verified_level = models.PositiveSmallIntegerField(null=True, blank=True)
    verified_by = models.ForeignKey(
        UserAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_claims",
    )
    verification_notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.user.regno_or_id} - {self.title} ({self.status})"


class FacultyGuidance(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="guidance_items",
    )
    faculty = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="issued_guidance",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guidance_items",
    )
    path_title = models.CharField(max_length=180)
    guidance_feedback = models.TextField()
    recommended_steps = models.TextField(blank=True)
    target_weeks = models.PositiveIntegerField(default=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Guidance for {self.student.user.regno_or_id}: {self.path_title}"