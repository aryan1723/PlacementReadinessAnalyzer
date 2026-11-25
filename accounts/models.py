from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class UserAccount(models.Model):
    ROLE_STUDENT = "STUDENT"
    ROLE_FACULTY = "FACULTY"
    ROLE_PLACEMENT_CELL = "PLACEMENT_CELL"
    ROLE_RECRUITER = "RECRUITER"
    ROLE_ADMIN = "ADMIN"

    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_FACULTY, "Faculty"),
        (ROLE_PLACEMENT_CELL, "Placement Cell"),
        (ROLE_RECRUITER, "Recruiter"),
        (ROLE_ADMIN, "Admin"),
    ]

    regno_or_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["regno_or_id"]

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.regno_or_id} - {self.name} ({self.role})"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )

    # Formal academic eligibility fields
    branch = models.CharField(max_length=50, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    backlogs = models.IntegerField(default=0)
    phone = models.CharField(max_length=25, blank=True)

    # Social & portfolio links
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    # Coding platform profiles
    leetcode_url = models.URLField(blank=True)
    hackerrank_url = models.URLField(blank=True)
    hackerearth_url = models.URLField(blank=True)
    other_coding_url = models.URLField(blank=True)

    # Resume / CV link and uploaded document
    cv_link = models.URLField(blank=True)
    cv_file = models.FileField(upload_to="cvs/", blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.regno_or_id} ({self.branch or 'No Branch'})"