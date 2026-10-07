"""
Clean and chart-friendly demo dataset for JIREN.

Creates:
- 1 global admin account
- 4 projects: Projet Equipe 1..4
- 4 realistic users per project
- default profile picture for everyone
- 5 sprints per project (3 closed, 1 active, 1 planned)
- richer tickets for charts and demo:
    1 epic
    6 stories
    3 bugs
    8 tasks
- tags, ticket links, attachments
- story point scheme for every project
- Git repositories for first 2 projects
- sprint capacities for per-user project
"""

import struct
import zlib
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils import timezone

from blog.models import (
    GitRepository,
    Project,
    ProjectMember,
    Sprint,
    SprintUserCapacity,
    StoryPointsScheme,
    Tag,
    Ticket,
    TicketAttachment,
    TicketLink,
)

PASSWORD = "testpass123"
SPRINT_DURATION_DAYS = 14

DATASET_USERS = [
    {
        "username": "admin",
        "email": "admin@jiren.dev",
        "first_name": "Admin",
        "last_name": "Jiren",
        "is_staff": True,
        "is_superuser": True,
    },

    # Projet Equipe 1
    {"username": "lucas.martin", "email": "lucas.martin@jiren.dev", "first_name": "Lucas", "last_name": "Martin"},
    {"username": "emma.dubois", "email": "emma.dubois@jiren.dev", "first_name": "Emma", "last_name": "Dubois"},
    {"username": "nathan.leroy", "email": "nathan.leroy@jiren.dev", "first_name": "Nathan", "last_name": "Leroy"},
    {"username": "chloe.bernard", "email": "chloe.bernard@jiren.dev", "first_name": "Chloe", "last_name": "Bernard"},

    # Projet Equipe 2
    {"username": "hugo.moreau", "email": "hugo.moreau@jiren.dev", "first_name": "Hugo", "last_name": "Moreau"},
    {"username": "lea.petit", "email": "lea.petit@jiren.dev", "first_name": "Lea", "last_name": "Petit"},
    {"username": "enzo.garcia", "email": "enzo.garcia@jiren.dev", "first_name": "Enzo", "last_name": "Garcia"},
    {"username": "camille.fontaine", "email": "camille.fontaine@jiren.dev", "first_name": "Camille", "last_name": "Fontaine"},

    # Projet Equipe 3
    {"username": "tom.rousseau", "email": "tom.rousseau@jiren.dev", "first_name": "Tom", "last_name": "Rousseau"},
    {"username": "ines.lambert", "email": "ines.lambert@jiren.dev", "first_name": "Ines", "last_name": "Lambert"},
    {"username": "jules.michel", "email": "jules.michel@jiren.dev", "first_name": "Jules", "last_name": "Michel"},
    {"username": "sarah.robin", "email": "sarah.robin@jiren.dev", "first_name": "Sarah", "last_name": "Robin"},

    # Projet Equipe 4
    {"username": "maxime.laurent", "email": "maxime.laurent@jiren.dev", "first_name": "Maxime", "last_name": "Laurent"},
    {"username": "akim.belkacem", "email": "akim.belkacem@jiren.dev", "first_name": "Akim", "last_name": "Belkacem"},
    {"username": "nathan.dolhen", "email": "nathan.dolhen@jiren.dev", "first_name": "Nathan", "last_name": "Dolhen"},
    {"username": "enzo.lherisson", "email": "enzo.lherisson@jiren.dev", "first_name": "Enzo", "last_name": "Lherisson"},
]

PROJECT_CONFIGS = [
    {
        "code": "EQ1",
        "name": "Projet Equipe 1",
        "description": "Project space for Equipe 1 demo dataset.",
        "members": ["lucas.martin", "emma.dubois", "nathan.leroy", "chloe.bernard"],
        "capacity_mode": Project.CAPACITY_MODE_GLOBAL,
        "global_capacity": 36,
        "epic_color": "#4F46E5",
    },
    {
        "code": "EQ2",
        "name": "Projet Equipe 2",
        "description": "Project space for Equipe 2 demo dataset.",
        "members": ["hugo.moreau", "lea.petit", "enzo.garcia", "camille.fontaine"],
        "capacity_mode": Project.CAPACITY_MODE_GLOBAL,
        "global_capacity": 34,
        "epic_color": "#0EA5E9",
    },
    {
        "code": "EQ3",
        "name": "Projet Equipe 3",
        "description": "Project space for Equipe 3 demo dataset.",
        "members": ["tom.rousseau", "ines.lambert", "jules.michel", "sarah.robin"],
        "capacity_mode": Project.CAPACITY_MODE_PER_USER,
        "global_capacity": None,
        "epic_color": "#10B981",
    },
    {
        "code": "EQ4",
        "name": "Projet Equipe 4",
        "description": "Project space for Equipe 4 demo dataset.",
        "members": ["maxime.laurent", "akim.belkacem", "nathan.dolhen", "enzo.lherisson"],
        "capacity_mode": Project.CAPACITY_MODE_GLOBAL,
        "global_capacity": 38,
        "epic_color": "#F59E0B",
    },
]

TAG_LABELS = ["frontend", "backend", "ui", "urgent", "testing", "documentation"]


# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

def clear_test_dataset():
    User.objects.filter(username__in=[u["username"] for u in DATASET_USERS]).delete()
    Project.objects.filter(code_prefix__in=[p["code"] for p in PROJECT_CONFIGS]).delete()


# -----------------------------------------------------------------------------
# Users
# -----------------------------------------------------------------------------

def create_dataset_users():
    users = []
    for data in DATASET_USERS:
        username = data["username"]
        user, _ = User.objects.get_or_create(username=username)

        user.email = data["email"]
        user.first_name = data["first_name"]
        user.last_name = data["last_name"]
        user.is_staff = data.get("is_staff", False)
        user.is_superuser = data.get("is_superuser", False)
        user.set_password(PASSWORD)
        user.save()

        if hasattr(user, "profile"):
            user.profile.image = "default.jpg"
            user.profile.save()

        users.append(user)
    return users


# -----------------------------------------------------------------------------
# Projects
# -----------------------------------------------------------------------------

def create_dataset_projects(users):
    users_by_username = {u.username: u for u in users}
    admin = users_by_username["admin"]
    today = timezone.now().date()
    projects = []

    for config in PROJECT_CONFIGS:
        project, _ = Project.objects.get_or_create(
            code_prefix=config["code"],
            defaults={
                "name": config["name"],
                "description": config["description"],
                "start_date": today - timedelta(days=70),
                "end_date": today + timedelta(days=90),
                "workload_unit": Project.WORKLOAD_UNIT_STORY_POINTS,
                "sprint_duration_days": SPRINT_DURATION_DAYS,
                "capacity_mode": config["capacity_mode"],
                "global_capacity": config["global_capacity"],
                "manager": admin,
            },
        )

        project.name = config["name"]
        project.description = config["description"]
        project.start_date = today - timedelta(days=70)
        project.end_date = today + timedelta(days=90)
        project.workload_unit = Project.WORKLOAD_UNIT_STORY_POINTS
        project.sprint_duration_days = SPRINT_DURATION_DAYS
        project.capacity_mode = config["capacity_mode"]
        project.global_capacity = config["global_capacity"]
        project.manager = admin
        project.save()

        ProjectMember.objects.get_or_create(
            project=project,
            user=admin,
            defaults={"role": ProjectMember.ROLE_CONTRIBUTOR},
        )

        for username in config["members"]:
            ProjectMember.objects.get_or_create(
                project=project,
                user=users_by_username[username],
                defaults={"role": ProjectMember.ROLE_CONTRIBUTOR},
            )

        projects.append(project)

    return projects

# -----------------------------------------------------------------------------
# Story points
# -----------------------------------------------------------------------------

def create_story_points_schemes(projects):
    schemes = []
    for project in projects:
        scheme, _ = StoryPointsScheme.objects.get_or_create(
            project=project,
            defaults={"scheme_type": StoryPointsScheme.FIBONACCI},
        )
        scheme.scheme_type = StoryPointsScheme.FIBONACCI
        scheme.save()
        schemes.append(scheme)
    return schemes


# -----------------------------------------------------------------------------
# Sprints
# -----------------------------------------------------------------------------

def create_dataset_sprints(projects, users):
    admin = next(u for u in users if u.username == "admin")
    today = timezone.now().date()
    sprints = []

    for project in projects:
        sprint_capacity_mode = (
            Sprint.CAPACITY_MODE_PER_USER
            if project.capacity_mode == Project.CAPACITY_MODE_PER_USER
            else Sprint.CAPACITY_MODE_GLOBAL
        )
        sprint_capacity = None if sprint_capacity_mode == Sprint.CAPACITY_MODE_PER_USER else int(project.global_capacity or 36)

        sprint_specs = [
            ("Sprint 1", Sprint.STATUS_CLOSED, today - timedelta(days=70), today - timedelta(days=57), "Set up dashboard and navigation."),
            ("Sprint 2", Sprint.STATUS_CLOSED, today - timedelta(days=56), today - timedelta(days=43), "Deliver backlog ordering and ticket management."),
            ("Sprint 3", Sprint.STATUS_CLOSED, today - timedelta(days=42), today - timedelta(days=29), "Stabilize sprint workflow and fix key bugs."),
            ("Sprint 4", Sprint.STATUS_ACTIVE, today - timedelta(days=14), today - timedelta(days=1), "Finalize core workflow and improve visibility."),
            ("Sprint 5", Sprint.STATUS_PLANNED, today + timedelta(days=1), today + timedelta(days=14), "Polish the product and prepare presentation."),
        ]

        for name, status, start_date, end_date, objective in sprint_specs:
            sprint, _ = Sprint.objects.get_or_create(
                project=project,
                name=name,
                defaults={
                    "objective": objective,
                    "status": status,
                    "capacity_mode": sprint_capacity_mode,
                    "capacity": sprint_capacity,
                    "start_date": start_date,
                    "end_date": end_date,
                    "created_by": admin,
                    "activated_at": timezone.now() - timedelta(days=14) if status == Sprint.STATUS_ACTIVE else None,
                    "closed_at": timezone.now() - timedelta(days=1) if status == Sprint.STATUS_CLOSED else None,
                },
            )

            sprint.objective = objective
            sprint.status = status
            sprint.capacity_mode = sprint_capacity_mode
            sprint.capacity = sprint_capacity
            sprint.start_date = start_date
            sprint.end_date = end_date
            sprint.created_by = admin
            sprint.activated_at = timezone.now() - timedelta(days=10) if status == Sprint.STATUS_ACTIVE else None
            sprint.closed_at = timezone.now() - timedelta(days=3) if status == Sprint.STATUS_CLOSED else None
            sprint.save()

            sprints.append(sprint)

    return sprints


def create_sprint_capacities(sprints, users):
    created = []
    users_by_username = {u.username: u for u in users}
    eq3_members = [
        users_by_username["tom.rousseau"],
        users_by_username["ines.lambert"],
        users_by_username["jules.michel"],
        users_by_username["sarah.robin"],
    ]

    for sprint in [s for s in sprints if s.project.code_prefix == "EQ3"]:
        if sprint.capacity_mode != Sprint.CAPACITY_MODE_PER_USER:
            continue

        for user, capacity in zip(eq3_members, [10, 9, 8, 9]):
            obj, _ = SprintUserCapacity.objects.get_or_create(
                sprint=sprint,
                user=user,
                defaults={"capacity": capacity},
            )
            obj.capacity = capacity
            obj.save()
            created.append(obj)

    return created


# -----------------------------------------------------------------------------
# Tags
# -----------------------------------------------------------------------------

def create_dataset_tags(projects):
    tags = []
    for project in projects:
        for label in TAG_LABELS:
            tag, _ = Tag.objects.get_or_create(project=project, name=label)
            tags.append(tag)
    return tags


# -----------------------------------------------------------------------------
# Ticket helpers
# -----------------------------------------------------------------------------

def _story_template(goal, benefit, developer_description, business_rules, done_when):
    return f"""As a user,

I want {goal}

so that {benefit}



Developer description

{developer_description}



Business rules

{business_rules}



Done when

{done_when}
"""


def _bug_description(summary, expected, actual):
    return f"""Problem

{summary}



Expected result

{expected}



Actual result

{actual}
"""


def _task_description(text):
    return text


def _project_tags(tags, project, *names):
    return [t for t in tags if t.project == project and t.name in names]


def _make_ticket(
    *,
    project,
    sprint,
    title,
    description,
    issue_type,
    status,
    priority,
    author,
    assignee=None,
    epic=None,
    story_points=0,
    initial_load=0,
    remaining_load=0,
    color=None,
    backlog_order=0,
):
    return Ticket.objects.create(
        project=project,
        sprint=sprint,
        title=title,
        description=description,
        issue_type=issue_type,
        status=status,
        priority=priority,
        author=author,
        assignee=assignee,
        epic=epic,
        story_points=story_points,
        initial_load=initial_load,
        remaining_load=remaining_load,
        color=color,
        backlog_order=backlog_order,
    )


# -----------------------------------------------------------------------------
# Tickets
# -----------------------------------------------------------------------------

def create_dataset_tickets(projects, sprints, users, tags):
    all_tickets = []

    for project in projects:
        members = [
            pm.user
            for pm in project.members.select_related("user").all()
            if pm.user.username != "admin"
        ]
        members = members[:4]

        sprint_1 = Sprint.objects.get(project=project, name="Sprint 1")
        sprint_2 = Sprint.objects.get(project=project, name="Sprint 2")
        sprint_3 = Sprint.objects.get(project=project, name="Sprint 3")
        sprint_4 = Sprint.objects.get(project=project, name="Sprint 4")

        config = next(c for c in PROJECT_CONFIGS if c["code"] == project.code_prefix)

        tickets = _create_project_ticket_set(
            project=project,
            sprint_1=sprint_1,
            sprint_2=sprint_2,
            sprint_3=sprint_3,
            sprint_4=sprint_4,
            members=members,
            tags=tags,
            epic_color=config["epic_color"],
        )
        all_tickets.extend(tickets)

    return all_tickets


def _create_project_ticket_set(project, sprint_1, sprint_2, sprint_3, sprint_4, members, tags, epic_color):
    a1, a2, a3, a4 = members
    T = Ticket.STATUS_TODO
    I = Ticket.STATUS_IN_PROGRESS
    D = Ticket.STATUS_DONE

    tickets = []
    order = 1

    epic = _make_ticket(
        project=project,
        sprint=None,
        title="Core project management workflow",
        description="Main epic covering the core project management workflow.",
        issue_type=Ticket.ISSUE_TYPE_EPIC,
        status=I,
        priority="HIGH",
        author=a1,
        assignee=None,
        color=epic_color,
        backlog_order=order,
    )
    epic.tags.set(_project_tags(tags, project, "frontend", "backend"))
    tickets.append(epic)
    order += 1

    story_specs = [
        {
            "title": "As a user, I want to access the project dashboard",
            "goal": "to access the project dashboard",
            "benefit": "I can quickly understand the current state of the project.",
            "developer": "Display the main project information, recent activity and key indicators on the dashboard page.",
            "rules": "The dashboard must be accessible to project members.\nThe displayed data must belong to the selected project only.",
            "done_when": "The user can open the dashboard.\nThe dashboard displays the main project information.\nThe page loads correctly without errors.",
            "sprint": sprint_1,
            "status": D,
            "priority": "HIGH",
            "points": 3,
            "initial": 3,
            "remaining": 0,
            "author": a1,
            "assignee": a1,
            "tags": ("frontend", "ui"),
        },
        {
            "title": "As a user, I want to manage the product backlog",
            "goal": "to manage the product backlog",
            "benefit": "I can organize and prioritize the work of the project.",
            "developer": "Allow users to view backlog items, reorder them and manage their priority inside the project.",
            "rules": "Only project members can access the backlog.\nOnly valid backlog items must be displayed.\nThe backlog order must be saved after changes.",
            "done_when": "The user can open the backlog page.\nStories and bugs are displayed in priority order.\nA ticket can be moved up or down in the backlog.",
            "sprint": sprint_2,
            "status": D,
            "priority": "HIGH",
            "points": 5,
            "initial": 5,
            "remaining": 0,
            "author": a2,
            "assignee": a2,
            "tags": ("backend",),
        },
        {
            "title": "As a user, I want to manage sprint content",
            "goal": "to manage sprint content",
            "benefit": "I can organize the work planned for the current sprint.",
            "developer": "Allow users to add tickets to a sprint, remove them and view the sprint objective and associated content.",
            "rules": "Only one sprint can be active at a time for a given project.\nOnly valid tickets can be assigned to a sprint.\nSprint information must remain linked to the correct project.",
            "done_when": "The user can open a sprint detail page.\nTickets can be added to the sprint.\nTickets can be removed from the sprint.\nThe sprint objective is displayed correctly.",
            "sprint": sprint_3,
            "status": D,
            "priority": "MEDIUM",
            "points": 5,
            "initial": 5,
            "remaining": 0,
            "author": a3,
            "assignee": a3,
            "tags": ("backend", "documentation"),
        },
        {
            "title": "As a user, I want to track work on a Kanban board",
            "goal": "to track work on a Kanban board",
            "benefit": "I can visualize the progress of the sprint.",
            "developer": "Display sprint tickets in Kanban columns and allow status changes through the board interface.",
            "rules": "Only tickets assigned to the selected sprint must appear on the board.\nEach ticket must appear in the column matching its current status.\nA status change must update the ticket correctly.",
            "done_when": "The user can open the Kanban board.\nTickets appear in the correct columns.\nA ticket can move from TODO to IN_PROGRESS and to DONE.\nThe board updates the ticket status successfully.",
            "sprint": sprint_4,
            "status": I,
            "priority": "HIGH",
            "points": 8,
            "initial": 8,
            "remaining": 3,
            "author": a4,
            "assignee": a4,
            "tags": ("frontend", "ui"),
        },
        {
            "title": "As a user, I want to manage ticket attachments",
            "goal": "to manage ticket attachments",
            "benefit": "I can keep project files directly linked to tickets.",
            "developer": "Allow users to upload, view and download attachments from the ticket detail page.",
            "rules": "Only allowed image formats may be uploaded.\nAttachments must remain linked to the correct ticket.",
            "done_when": "The user can upload a file.\nThe attachment appears on the ticket detail page.\nThe attachment can be opened successfully.",
            "sprint": sprint_4,
            "status": T,
            "priority": "MEDIUM",
            "points": 3,
            "initial": 3,
            "remaining": 3,
            "author": a1,
            "assignee": a2,
            "tags": ("backend", "testing"),
        },
        {
            "title": "As a user, I want to view project statistics",
            "goal": "to view project statistics",
            "benefit": "I can better understand project progress and team activity.",
            "developer": "Display project metrics such as completed work, sprint distribution and other key indicators.",
            "rules": "Statistics must only use data from the selected project.\nThe page must stay available even if the project has limited history.",
            "done_when": "The user can open the statistics page.\nCharts are displayed correctly.\nCompleted and remaining work are visible.",
            "sprint": None,
            "status": T,
            "priority": "HIGH",
            "points": 5,
            "initial": 5,
            "remaining": 5,
            "author": a2,
            "assignee": a3,
            "tags": ("frontend", "documentation"),
        },
    ]

    story_objects = []
    for spec in story_specs:
        obj = _make_ticket(
            project=project,
            sprint=spec["sprint"],
            title=spec["title"],
            description=_story_template(
                goal=spec["goal"],
                benefit=spec["benefit"],
                developer_description=spec["developer"],
                business_rules=spec["rules"],
                done_when=spec["done_when"],
            ),
            issue_type=Ticket.ISSUE_TYPE_STORY,
            status=spec["status"],
            priority=spec["priority"],
            author=spec["author"],
            assignee=spec["assignee"],
            epic=epic,
            story_points=spec["points"],
            initial_load=spec["initial"],
            remaining_load=spec["remaining"],
            backlog_order=order,
        )
        obj.tags.set(_project_tags(tags, project, *spec["tags"]))
        story_objects.append(obj)
        tickets.append(obj)
        order += 1

    bug_specs = [
        {
            "title": "Kanban board does not refresh after status change",
            "summary": "When a ticket status changes on the Kanban board, the column does not always refresh correctly.",
            "expected": "The board updates immediately after the status change.",
            "actual": "The user sometimes needs to refresh the page manually.",
            "sprint": sprint_2,
            "status": D,
            "priority": "HIGH",
            "points": 2,
            "initial": 2,
            "remaining": 0,
            "author": a1,
            "assignee": a2,
            "tags": ("frontend", "urgent"),
        },
        {
            "title": "Backlog ordering becomes inconsistent after moving stories",
            "summary": "When several stories are reordered in the backlog, their position may not update correctly.",
            "expected": "The new order remains consistent after the page reload.",
            "actual": "Some items appear in the wrong order after a refresh.",
            "sprint": sprint_3,
            "status": D,
            "priority": "MEDIUM",
            "points": 3,
            "initial": 3,
            "remaining": 0,
            "author": a2,
            "assignee": a3,
            "tags": ("backend", "testing"),
        },
        {
            "title": "Attachment preview fails on ticket detail page",
            "summary": "An uploaded image does not always render in the ticket detail page preview.",
            "expected": "The attachment preview is visible immediately.",
            "actual": "The preview sometimes stays blank until the page is refreshed.",
            "sprint": sprint_4,
            "status": T,
            "priority": "MEDIUM",
            "points": 2,
            "initial": 2,
            "remaining": 2,
            "author": a3,
            "assignee": a4,
            "tags": ("frontend", "urgent"),
        },
    ]

    bug_objects = []
    for spec in bug_specs:
        obj = _make_ticket(
            project=project,
            sprint=spec["sprint"],
            title=spec["title"],
            description=_bug_description(
                summary=spec["summary"],
                expected=spec["expected"],
                actual=spec["actual"],
            ),
            issue_type=Ticket.ISSUE_TYPE_BUG,
            status=spec["status"],
            priority=spec["priority"],
            author=spec["author"],
            assignee=spec["assignee"],
            epic=epic,
            story_points=spec["points"],
            initial_load=spec["initial"],
            remaining_load=spec["remaining"],
            backlog_order=order,
        )
        obj.tags.set(_project_tags(tags, project, *spec["tags"]))
        bug_objects.append(obj)
        tickets.append(obj)
        order += 1

    task_specs = [
        ("Create dashboard layout", "Create the main layout of the project dashboard including header, summary cards and navigation.", D, "MEDIUM", 2, 0, a1, a1, ("frontend", "ui")),
        ("Implement backlog ordering logic", "Implement the logic used to move stories up and down in the backlog.", D, "HIGH", 3, 0, a2, a2, ("backend",)),
        ("Create sprint detail page", "Create the sprint detail page displaying objective, dates and sprint content.", D, "MEDIUM", 3, 0, a3, a3, ("frontend",)),
        ("Implement Kanban status update", "Implement ticket status updates from the Kanban board interface.", I, "HIGH", 5, 2, a4, a4, ("frontend", "urgent")),
        ("Add ticket tag support", "Allow tags to be attached to tickets and displayed in ticket views.", D, "LOW", 2, 0, a1, a2, ("backend", "documentation")),
        ("Create ticket attachment upload", "Allow users to attach files to a ticket and display them in the detail page.", I, "MEDIUM", 3, 1, a2, a4, ("backend", "testing")),
        ("Implement project statistics cards", "Create the statistics cards visible on the project analytics page.", T, "MEDIUM", 5, 5, a3, a1, ("frontend", "documentation")),
        ("Add ticket filtering by tag", "Allow ticket lists to be filtered using tags.", T, "LOW", 2, 2, a4, a3, ("frontend", "ui")),
    ]

    task_objects = []
    for title, description, status, priority, initial, remaining, author, assignee, tag_names in task_specs:
        obj = _make_ticket(
            project=project,
            sprint=None,
            title=title,
            description=_task_description(description),
            issue_type=Ticket.ISSUE_TYPE_TASK,
            status=status,
            priority=priority,
            author=author,
            assignee=assignee,
            epic=epic,
            initial_load=initial,
            remaining_load=remaining,
            backlog_order=order,
        )
        obj.tags.set(_project_tags(tags, project, *tag_names))
        task_objects.append(obj)
        tickets.append(obj)
        order += 1

    # Ticket links to exercise link feature
    TicketLink.objects.get_or_create(
        source_ticket=story_objects[0],
        target_ticket=story_objects[1],
        link_type=TicketLink.TYPE_RELATES_TO,
    )
    TicketLink.objects.get_or_create(
        source_ticket=story_objects[2],
        target_ticket=story_objects[3],
        link_type=TicketLink.TYPE_RELATES_TO,
    )
    TicketLink.objects.get_or_create(
        source_ticket=bug_objects[0],
        target_ticket=story_objects[3],
        link_type=TicketLink.TYPE_BLOCKED_BY,
    )
    TicketLink.objects.get_or_create(
        source_ticket=task_objects[1],
        target_ticket=story_objects[1],
        link_type=TicketLink.TYPE_RELATES_TO,
    )
    TicketLink.objects.get_or_create(
        source_ticket=task_objects[5],
        target_ticket=story_objects[4],
        link_type=TicketLink.TYPE_RELATES_TO,
    )

    return tickets


# -----------------------------------------------------------------------------
# Ticket links / attachments / git repos
# -----------------------------------------------------------------------------

def create_ticket_links(project_tickets_map):
    # Links are already created inside _create_project_ticket_set.
    # We keep this function for compatibility with the management command.
    return list(TicketLink.objects.all())


def create_ticket_attachments(tickets_with_attachments):
    created = []
    for ticket in tickets_with_attachments:
        attachment = TicketAttachment(ticket=ticket)
        attachment.file.save(
            f"attachment_ticket_{ticket.id}.png",
            ContentFile(_minimal_png(ticket.id)),
            save=True,
        )
        created.append(attachment)
    return created


def create_git_repositories(project_1, project_2):
    repos = []

    repo_1, _ = GitRepository.objects.get_or_create(
        project=project_1,
        defaults={
            "repository_url": "https://github.com/jiren-demo/projet-equipe-1",
            "repository_type": GitRepository.REPOSITORY_TYPE_GITHUB,
            "is_private": False,
        },
    )
    repos.append(repo_1)

    repo_2, _ = GitRepository.objects.get_or_create(
        project=project_2,
        defaults={
            "repository_url": "https://gitlab.com/jiren-demo/projet-equipe-2",
            "repository_type": GitRepository.REPOSITORY_TYPE_GITLAB,
            "is_private": False,
        },
    )
    repos.append(repo_2)

    return repos


# -----------------------------------------------------------------------------
# Minimal PNG generator
# -----------------------------------------------------------------------------

def _minimal_png(seed):
    r = (seed * 47 + 3) % 256
    g = (seed * 97 + 7) % 256
    b = (seed * 137 + 11) % 256
    raw = struct.pack(">BBBBBBBB", 0, r, g, b, 255, r, g, b)
    compressed = zlib.compress(raw)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(chunk_type, data):
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)