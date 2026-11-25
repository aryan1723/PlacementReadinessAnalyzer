import uuid
from django.db import models
from accounts.models import UserAccount
from drives_readiness.models import PlacementDrive


class SupportTicket(models.Model):
    TARGET_ADMIN = UserAccount.ROLE_ADMIN
    TARGET_PLACEMENT = UserAccount.ROLE_PLACEMENT_CELL
    TARGET_FACULTY = UserAccount.ROLE_FACULTY
    TARGET_RECRUITER = UserAccount.ROLE_RECRUITER

    TARGET_ROLE_CHOICES = [
        (TARGET_PLACEMENT, "Placement Cell"),
        (TARGET_FACULTY, "Faculty"),
        (TARGET_RECRUITER, "Recruiter"),
        (TARGET_ADMIN, "System Admin"),
    ]

    STATUS_OPEN = "OPEN"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    ]

    PRIORITY_NORMAL = "NORMAL"
    PRIORITY_URGENT = "URGENT"

    PRIORITY_CHOICES = [
        (PRIORITY_NORMAL, "Normal"),
        (PRIORITY_URGENT, "Urgent"),
    ]

    ticket_code = models.CharField(max_length=20, unique=True, editable=False)
    created_by = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="created_tickets",
    )
    target_role = models.CharField(max_length=20, choices=TARGET_ROLE_CHOICES)
    related_drive = models.ForeignKey(
        PlacementDrive,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
    )
    subject = models.CharField(max_length=180)
    description = models.TextField()
    priority = models.CharField(
        max_length=15,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = f"TKT-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_code} [{self.target_role}] - {self.subject}"


class TicketReply(models.Model):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    sender = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="ticket_replies",
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply by {self.sender.regno_or_id} on {self.ticket.ticket_code}"