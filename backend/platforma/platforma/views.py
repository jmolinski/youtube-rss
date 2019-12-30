from django.shortcuts import render_to_response
from .models import Assignment, AssignmentParticipant, AssignmentCyclePair
from django.conf import settings


def home(request):
    assignments = "".join(
        [
            f'<option value="{a[0]}">{a[1]}</option>'
            for a in Assignment.objects.all().values_list("pk", "name")
        ]
    )

    assign = Assignment.objects.all().prefetch_related("participants")

    return render_to_response(
        template_name="platforma/index.html",
        context={
            "assignments": assignments,
            "assign": assign,
            "REDIRECT_PREFIX": settings.REDIRECT_PREFIX,
        },
    )


def render_exception(e):
    return render_to_response(
        template_name="platforma/error.html",
        context={
            "error": f"\n{str(e)}<br/>{repr(e)}",
            "REDIRECT_PREFIX": settings.REDIRECT_PREFIX,
        },
    )


def register_for_assignment(request):
    first_name = request.POST.get("first_name", "-1")
    last_name = request.POST.get("last_name", "-1")
    email = request.POST.get("email", "-1")
    assignment = request.POST.get("assignment_id", "-1")
    obj = AssignmentParticipant(
        first_name=first_name,
        last_name=last_name,
        email=email,
        assignment_id=int(assignment),
    )

    try:
        obj.save()
    except Exception as e:
        return render_exception(e)

    return home(request)


def create_cycle(assignment_id):
    participants = AssignmentParticipant.objects.filter(
        assignment_id=assignment_id
    ).exclude(authored__assignment__exact=assignment_id)
    ids = list(participants.values_list("pk", flat=True))

    if not ids:
        return

    ids += [ids[0]]
    pairs = zip(ids, ids[1:])

    for author, reviewer in pairs:
        AssignmentCyclePair.objects.create(
            author_id=author, reviewer_id=reviewer, assignment_id=assignment_id
        )


def trigger_create_cycle(request):
    assignment_id = request.GET.get("assignment", "-1")
    passcode = request.GET.get("passcode", "-1")

    if passcode != settings.PASSCODE:
        raise ValueError("wrong passcode")

    create_cycle(assignment_id)

    return home(request)
