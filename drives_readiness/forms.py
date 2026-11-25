from django import forms
from accounts.models import UserAccount
from .models import DriveApplication, DriveSkillRequirement, PlacementDrive, RecruiterGrant


class PlacementDriveForm(forms.ModelForm):
    class Meta:
        model = PlacementDrive
        fields = [
            "company_name",
            "role_title",
            "ctc_package",
            "job_location",
            "application_deadline",
            "min_cgpa",
            "max_backlogs",
            "allowed_branches",
            "graduation_year",
            "is_active",
            "description",
        ]
        widgets = {
            "application_deadline": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_min_cgpa(self):
        val = self.cleaned_data.get("min_cgpa")
        if val is not None and (val < 0 or val > 10):
            raise forms.ValidationError("Minimum CGPA must be between 0.00 and 10.00.")
        return val

    def clean_max_backlogs(self):
        val = self.cleaned_data.get("max_backlogs")
        if val is not None and val < 0:
            raise forms.ValidationError("Maximum backlogs cannot be negative.")
        return val


class DriveSkillRequirementForm(forms.ModelForm):
    LEVEL_CHOICES = [
        (1, "Level 1 — Foundational"),
        (2, "Level 2 — Applied"),
        (3, "Level 3 — Proficient"),
        (4, "Level 4 — Advanced"),
    ]

    min_level = forms.TypedChoiceField(
        label="Minimum Verified Level",
        choices=LEVEL_CHOICES,
        coerce=int,
        initial=2,
    )

    class Meta:
        model = DriveSkillRequirement
        fields = ["skill", "min_level", "weight"]
        labels = {
            "weight": "Benchmark Weight (1–5)",
        }

    def clean_weight(self):
        w = self.cleaned_data.get("weight") or 1
        if w < 1 or w > 5:
            raise forms.ValidationError("Weight must be between 1 and 5.")
        return w


class RecruiterGrantForm(forms.ModelForm):
    class Meta:
        model = RecruiterGrant
        fields = ["recruiter", "drive", "cohort_branch", "is_active"]

    def __init__(self, *args, **kwargs):
        drive_fixed = kwargs.pop("drive_fixed", None)
        super().__init__(*args, **kwargs)
        self.fields["recruiter"].queryset = UserAccount.objects.filter(
            role=UserAccount.ROLE_RECRUITER, is_active=True
        ).order_by("regno_or_id")
        if drive_fixed is not None:
            self.fields["drive"].queryset = PlacementDrive.objects.filter(id=drive_fixed.id)
            self.fields["drive"].initial = drive_fixed


class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = DriveApplication
        fields = ["status"]