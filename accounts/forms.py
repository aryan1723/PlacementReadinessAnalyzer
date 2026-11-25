from django import forms
from .models import StudentProfile, UserAccount


class LoginForm(forms.Form):
    regno_or_id = forms.CharField(label="Regno. / Staff or Admin ID", max_length=50)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


class StudentSignupForm(forms.Form):
    name = forms.CharField(label="Full Name", max_length=120)
    regno_or_id = forms.CharField(label="Registration Number", max_length=50)
    email = forms.EmailField(label="Email Address")
    password = forms.CharField(label="Password", min_length=6, widget=forms.PasswordInput)

    def clean_regno_or_id(self):
        val = self.cleaned_data["regno_or_id"].strip()
        if UserAccount.objects.filter(regno_or_id__iexact=val).exists():
            raise forms.ValidationError("This registration number is already registered.")
        return val

    def clean_email(self):
        val = self.cleaned_data["email"].strip().lower()
        if UserAccount.objects.filter(email__iexact=val).exists():
            raise forms.ValidationError("This email address is already registered.")
        return val


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            "branch",
            "graduation_year",
            "cgpa",
            "backlogs",
            "phone",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "leetcode_url",
            "hackerrank_url",
            "hackerearth_url",
            "other_coding_url",
            "cv_link",
            "cv_file",
        ]

    def clean_cgpa(self):
        cgpa = self.cleaned_data.get("cgpa")
        if cgpa is not None and (cgpa < 0 or cgpa > 10):
            raise forms.ValidationError("CGPA must be between 0.00 and 10.00.")
        return cgpa

    def clean_backlogs(self):
        backlogs = self.cleaned_data.get("backlogs")
        if backlogs is not None and backlogs < 0:
            raise forms.ValidationError("Backlogs cannot be negative.")
        return backlogs


class AdminAccountCreateForm(forms.Form):
    regno_or_id = forms.CharField(label="ID / Regno.", max_length=50)
    name = forms.CharField(label="Full Name", max_length=120)
    email = forms.EmailField(label="Email Address")
    role = forms.ChoiceField(label="Account Role", choices=UserAccount.ROLE_CHOICES)
    password = forms.CharField(label="Initial Password", min_length=6, widget=forms.PasswordInput)
    is_active = forms.BooleanField(label="Active Account", required=False, initial=True)

    def clean_regno_or_id(self):
        val = self.cleaned_data["regno_or_id"].strip()
        if UserAccount.objects.filter(regno_or_id__iexact=val).exists():
            raise forms.ValidationError("An account with this ID / Regno. already exists.")
        return val

    def clean_email(self):
        val = self.cleaned_data["email"].strip().lower()
        if UserAccount.objects.filter(email__iexact=val).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return val


class AdminAccountEditForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Reset Password (leave blank to keep current)",
        min_length=6,
        required=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = UserAccount
        fields = ["regno_or_id", "name", "email", "role", "is_active"]

    def clean_regno_or_id(self):
        val = self.cleaned_data["regno_or_id"].strip()
        qs = UserAccount.objects.filter(regno_or_id__iexact=val).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Another account already uses this ID / Regno.")
        return val

    def clean_email(self):
        val = self.cleaned_data["email"].strip().lower()
        qs = UserAccount.objects.filter(email__iexact=val).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Another account already uses this email.")
        return val