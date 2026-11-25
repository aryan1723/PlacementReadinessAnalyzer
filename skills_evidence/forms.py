from django import forms
from accounts.models import StudentProfile
from .models import EvidenceClaim, FacultyGuidance, Skill


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name", "category", "dimension"]


class CertificationClaimForm(forms.ModelForm):
    class Meta:
        model = EvidenceClaim
        fields = [
            "skill",
            "title",
            "organization",
            "credential_id",
            "issue_date",
            "duration_weeks",
            "duration_hours",
            "score_text",
            "proof_link",
            "certificate_document",
            "description",
        ]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class ProjectClaimForm(forms.ModelForm):
    class Meta:
        model = EvidenceClaim
        fields = [
            "skill",
            "title",
            "project_role",
            "tech_stack",
            "proof_link",
            "proof_attachment",
            "description",
        ]
        labels = {
            "proof_link": "GitHub / Live Deployment URL",
            "proof_attachment": "Architecture / Demo Document (Optional)",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class AcademicClaimForm(forms.ModelForm):
    class Meta:
        model = EvidenceClaim
        fields = [
            "skill",
            "title",
            "academic_result",
            "academic_grade",
            "proof_attachment",
            "description",
        ]
        labels = {
            "title": "Course / Academic Milestone Title",
            "proof_attachment": "Transcript / Marksheet Proof",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class InternshipClaimForm(forms.ModelForm):
    class Meta:
        model = EvidenceClaim
        fields = [
            "skill",
            "title",
            "organization",
            "project_role",
            "tech_stack",
            "duration_weeks",
            "proof_link",
            "certificate_document",
            "description",
        ]
        labels = {
            "title": "Internship / Experience Title",
            "project_role": "Role / Designation",
            "certificate_document": "Offer / Completion Letter",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class AssessmentClaimForm(forms.ModelForm):
    class Meta:
        model = EvidenceClaim
        fields = [
            "skill",
            "title",
            "organization",
            "score_text",
            "issue_date",
            "proof_link",
            "proof_attachment",
            "description",
        ]
        labels = {
            "title": "Hackathon / Coding Assessment Title",
            "organization": "Platform / Organizer",
            "score_text": "Rank / Score / Percentile",
        }
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


CLAIM_FORM_MAP = {
    EvidenceClaim.TYPE_CERTIFICATION: CertificationClaimForm,
    EvidenceClaim.TYPE_PROJECT: ProjectClaimForm,
    EvidenceClaim.TYPE_ACADEMIC: AcademicClaimForm,
    EvidenceClaim.TYPE_INTERNSHIP: InternshipClaimForm,
    EvidenceClaim.TYPE_ASSESSMENT: AssessmentClaimForm,
}


class VerifyClaimForm(forms.ModelForm):
    LEVEL_CHOICES = [
        ("", "Select Verified Level (Required if Verifying)"),
        (1, "Level 1 — Foundational / Awareness"),
        (2, "Level 2 — Applied / Guided Implementation"),
        (3, "Level 3 — Proficient / Independent Delivery"),
        (4, "Level 4 — Advanced / Production Mastery"),
    ]

    status = forms.ChoiceField(
        label="Verification Decision",
        choices=[
            (EvidenceClaim.STATUS_VERIFIED, "Verify Claim"),
            (EvidenceClaim.STATUS_DECLINED, "Decline Claim"),
            (EvidenceClaim.STATUS_PENDING, "Keep Pending"),
        ],
    )
    verified_level = forms.TypedChoiceField(
        label="Verified Proficiency Level (1–4)",
        choices=LEVEL_CHOICES,
        coerce=lambda x: int(x) if x != "" else None,
        required=False,
    )

    class Meta:
        model = EvidenceClaim
        fields = ["status", "verified_level", "verification_notes"]
        widgets = {
            "verification_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        level = cleaned.get("verified_level")
        notes = (cleaned.get("verification_notes") or "").strip()

        if status == EvidenceClaim.STATUS_VERIFIED and not level:
            self.add_error("verified_level", "Assign a verified level (1–4) when verifying a claim.")
        if status == EvidenceClaim.STATUS_DECLINED:
            cleaned["verified_level"] = None
            if not notes:
                self.add_error("verification_notes", "Provide clear feedback explaining why this claim was declined.")
        if status == EvidenceClaim.STATUS_PENDING:
            cleaned["verified_level"] = None
        return cleaned


class FacultyGuidanceForm(forms.ModelForm):
    class Meta:
        model = FacultyGuidance
        fields = ["student", "skill", "path_title", "guidance_feedback", "recommended_steps", "target_weeks"]
        widgets = {
            "guidance_feedback": forms.Textarea(attrs={"rows": 3}),
            "recommended_steps": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = StudentProfile.objects.select_related("user").order_by(
            "user__regno_or_id"
        )