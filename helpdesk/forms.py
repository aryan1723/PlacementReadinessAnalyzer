from django import forms
from drives_readiness.models import PlacementDrive
from .models import SupportTicket, TicketReply


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["target_role", "related_drive", "priority", "subject", "description"]
        labels = {
            "target_role": "Target Department / Role",
            "related_drive": "Related Placement Drive (Optional)",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["related_drive"].queryset = PlacementDrive.objects.all().order_by("-created_at")
        self.fields["related_drive"].required = False


class TicketReplyForm(forms.ModelForm):
    class Meta:
        model = TicketReply
        fields = ["message"]
        labels = {
            "message": "Reply Message",
        }
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
        }


class TicketStatusForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["status"]