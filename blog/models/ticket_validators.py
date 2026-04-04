from django.db.models import Sum

LOAD_TYPES = frozenset(["STORY", "BUG", "TASK"])
STORY_BUG_TYPES = frozenset(["STORY", "BUG"])
EPIC_TASK_TYPES = frozenset(["EPIC", "TASK"])


def validate_epic_hierarchy(issue_type, epic, project_id, errors):
    if not epic:
        return
    if issue_type == "EPIC":
        errors["epic"] = "Epic cannot depend on another epic."
    elif epic.project_id != project_id:
        errors["epic"] = "Parent epic must be in same project."


def validate_sprint_rules(sprint, issue_type, project_id, errors):
    if not sprint:
        return
    if sprint.project_id != project_id:
        errors["sprint"] = "Sprint must be in same project."
        return
    if sprint.status == "CLOSED":
        errors["sprint"] = "Cannot add to closed sprint."
        return
    if issue_type not in STORY_BUG_TYPES:
        errors["sprint"] = "Only stories/bugs can join sprints."


def validate_tags(tags_manager, project, errors):
    invalid_tags = tags_manager.exclude(project=project)
    if invalid_tags.exists():
        names = ", ".join(invalid_tags.values_list("name", flat=True))
        errors["tags"] = f"Tags must be in this project: {names}"


def validate_story_points_rules(issue_type, story_points, errors):
    if issue_type in STORY_BUG_TYPES and story_points < 1:
        errors["story_points"] = "Stories/bugs need ≥1 story points."
    if issue_type in EPIC_TASK_TYPES and story_points != 0:
        errors["story_points"] = "Only stories/bugs have story points."


def validate_initial_load_immutable(pk, initial_load, ticket_model, errors):
    if not pk:
        return
    original = ticket_model.objects.filter(pk=pk).only("initial_load").first()
    if original and initial_load != original.initial_load:
        errors["initial_load"] = "Initial load cannot change after creation."


def validate_load_rules(issue_type, initial_load, remaining_load, errors):
    if issue_type in LOAD_TYPES:
        if remaining_load > initial_load:
            errors["remaining_load"] = "Remaining cannot exceed initial."
    else:
        if initial_load != 0:
            errors["initial_load"] = "Only stories/bugs/tasks have load."
        if remaining_load != 0:
            errors["remaining_load"] = "Only stories/bugs/tasks have load."


def validate_color(issue_type, color, errors):
    if issue_type != "EPIC" and color:
        errors["color"] = "Only epics have colors."


def validate_global_sprint_capacity(sprint, ticket_pk, story_points, ticket_model, errors):
    other_points = (
        ticket_model.objects.filter(
            sprint=sprint,
            issue_type__in=list(STORY_BUG_TYPES),
        )
        .exclude(pk=ticket_pk)
        .aggregate(total=Sum("story_points"))
        .get("total") or 0
    )
    new_total = other_points + story_points
    if sprint.capacity and new_total > sprint.capacity:
        errors["sprint"] = f"Would exceed capacity: {new_total}/{sprint.capacity}"


def validate_per_user_sprint_capacity(sprint, ticket_pk, story_points, assignee, capacity_model, ticket_model, errors):
    total_cap = sprint.configured_capacity()
    other_points = (
        ticket_model.objects.filter(
            sprint=sprint,
            issue_type__in=list(STORY_BUG_TYPES),
        )
        .exclude(pk=ticket_pk)
        .aggregate(total=Sum("story_points"))
        .get("total") or 0
    )
    new_total = other_points + story_points

    if total_cap <= 0:
        errors["sprint"] = "Configure user capacity first."
        return

    if not assignee:
        errors["assignee"] = "Assignee required for per-user sprint."
        return

    user_cap = capacity_model.objects.filter(sprint=sprint, user=assignee).first()
    if not user_cap:
        errors["assignee"] = "Assignee has no capacity."
        return

    user_points = (
        ticket_model.objects.filter(
            sprint=sprint,
            assignee=assignee,
            issue_type__in=list(STORY_BUG_TYPES),
        )
        .exclude(pk=ticket_pk)
        .aggregate(total=Sum("story_points"))
        .get("total") or 0
    )

    if user_points + story_points > user_cap.capacity:
        errors["story_points"] = f"Exceeds {assignee.username} capacity"

    if total_cap > 0 and new_total > total_cap:
        errors["sprint"] = f"Exceeds sprint total: {new_total}/{total_cap}"
