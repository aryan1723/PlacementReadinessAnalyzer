from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import UserAccount
from accounts.views import get_current_account

from .forms import SupportTicketForm, TicketReplyForm, TicketStatusForm
from .models import SupportTicket


def helpdesk_view(request):
    account = get_current_account(request)
    if not account:
        return redirect("/login/")

    status_filter = request.GET.get("status", "").strip().upper()
    msg = request.GET.get("msg", "")

    if request.method == "POST":
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = account
            ticket.save()
            return redirect(f"/helpdesk/?msg=Raised+ticket+{ticket.ticket_code}")
    else:
        form = SupportTicketForm()

    raised_tickets = SupportTicket.objects.filter(created_by=account).select_related(
        "created_by", "related_drive"
    )

    if account.role == UserAccount.ROLE_ADMIN:
        incoming_tickets = SupportTicket.objects.exclude(created_by=account).select_related(
            "created_by", "related_drive"
        )
    else:
        incoming_tickets = (
            SupportTicket.objects.filter(target_role=account.role)
            .exclude(created_by=account)
            .select_related("created_by", "related_drive")
        )

    if status_filter in dict(SupportTicket.STATUS_CHOICES):
        raised_tickets = raised_tickets.filter(status=status_filter)
        incoming_tickets = incoming_tickets.filter(status=status_filter)

    return render(
        request,
        "helpdesk.html",
        {
            "account": account,
            "form": form,
            "raised_tickets": raised_tickets,
            "incoming_tickets": incoming_tickets,
            "status_filter": status_filter,
            "status_choices": SupportTicket.STATUS_CHOICES,
            "msg": msg,
        },
    )


def ticket_detail_view(request, ticket_code):
    account = get_current_account(request)
    if not account:
        return redirect("/login/")

    ticket = get_object_or_404(
        SupportTicket.objects.select_related("created_by", "related_drive").prefetch_related(
            "replies__sender"
        ),
        ticket_code=ticket_code,
    )

    can_access = (
        account.role == UserAccount.ROLE_ADMIN
        or ticket.created_by_id == account.id
        or ticket.target_role == account.role
    )
    if not can_access:
        return redirect("/helpdesk/")

    can_change_status = (
        account.role == UserAccount.ROLE_ADMIN
        or ticket.target_role == account.role
        or ticket.created_by_id == account.id
    )

    if request.method == "POST":
        action = request.POST.get("action", "reply")
        if action == "status" and can_change_status:
            status_form = TicketStatusForm(request.POST, instance=ticket)
            reply_form = TicketReplyForm()
            if status_form.is_valid():
                status_form.save()
                return redirect(f"/helpdesk/{ticket.ticket_code}/?msg=Ticket+status+updated")
        else:
            reply_form = TicketReplyForm(request.POST)
            status_form = TicketStatusForm(instance=ticket)
            if reply_form.is_valid():
                reply = reply_form.save(commit=False)
                reply.ticket = ticket
                reply.sender = account
                reply.save()
                if ticket.status == SupportTicket.STATUS_OPEN and ticket.created_by_id != account.id:
                    ticket.status = SupportTicket.STATUS_IN_PROGRESS
                ticket.save()
                return redirect(f"/helpdesk/{ticket.ticket_code}/?msg=Reply+posted")
    else:
        reply_form = TicketReplyForm()
        status_form = TicketStatusForm(instance=ticket)

    return render(
        request,
        "ticket_detail.html",
        {
            "account": account,
            "ticket": ticket,
            "replies": ticket.replies.all(),
            "reply_form": reply_form,
            "status_form": status_form,
            "can_change_status": can_change_status,
            "msg": request.GET.get("msg", ""),
        },
    )