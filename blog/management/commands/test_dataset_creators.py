"""
Data creation helpers for the create_test_dataset management command.
Covers every model in the blog app: Project, Sprint, SprintUserCapacity,
Ticket (EPIC/STORY/BUG/TASK), Tag, TicketLink, TicketAttachment,
StoryPointsScheme, GitRepository, ProjectMember.
"""
import io
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

# ── Constants ────────────────────────────────────────────────────────────────

SPRINT_CAPACITY_POINTS = 40
SPRINT_DURATION_DAYS = 14
MEMBER_CAPACITY_POINTS = 10
MAX_CONTRIBUTORS_DISPLAYED = 5
CLOSED_SPRINT_COUNT = 3
CLOSED_SPRINT_GAP_DAYS = 14

DATASET_USERS = [
    {"username": "jiren_admin",    "email": "admin@jiren.dev",    "first_name": "Admin",    "last_name": "Jiren",     "is_staff": True},
    {"username": "alice_dev",      "email": "alice@jiren.dev",    "first_name": "Alice",    "last_name": "Durand"},
    {"username": "bob_dev",        "email": "bob@jiren.dev",      "first_name": "Bob",      "last_name": "Martin"},
    {"username": "charlie_dev",    "email": "charlie@jiren.dev",  "first_name": "Charlie",  "last_name": "Petit"},
    {"username": "elena_design",   "email": "elena@jiren.dev",    "first_name": "Elena",    "last_name": "Voss"},
    {"username": "sara_design",    "email": "sara@jiren.dev",     "first_name": "Sara",     "last_name": "Blanc"},
    {"username": "marcus_qa",      "email": "marcus@jiren.dev",   "first_name": "Marcus",   "last_name": "Dahl"},
    {"username": "jordan_qa",      "email": "jordan@jiren.dev",   "first_name": "Jordan",   "last_name": "Cruz"},
    {"username": "leo_product",    "email": "leo@jiren.dev",      "first_name": "Leo",      "last_name": "Bernard"},
    {"username": "nadia_product",  "email": "nadia@jiren.dev",    "first_name": "Nadia",    "last_name": "Kowalski"},
]

TAG_LABELS = [
    "infrastructure", "frontend", "backend", "database",
    "security", "ui-ux", "testing", "documentation",
]


# ── Cleanup ──────────────────────────────────────────────────────────────────

def clear_test_dataset():
    User.objects.filter(username__in=[u["username"] for u in DATASET_USERS]).delete()
    Project.objects.filter(code_prefix__in=["QIR", "API2", "MOB"]).delete()


# ── Users ────────────────────────────────────────────────────────────────────

def create_dataset_users():
    users = []
    for data in DATASET_USERS:
        is_staff = data.pop("is_staff", False)
        user, created = User.objects.get_or_create(
            username=data["username"],
            defaults={**data, "is_staff": is_staff},
        )
        if created:
            user.set_password("testpass123")
            user.save(update_fields=["password"])
        data["is_staff"] = is_staff
        users.append(user)
    return users


# ── Projects ─────────────────────────────────────────────────────────────────

def create_dataset_projects(users):
    admin, alice, bob, charlie, elena, sara, marcus, jordan, leo, nadia = users
    now = timezone.now()

    qir = _build_project(
        code="QIR",
        name="Quantum Interface Redesign",
        description="Full redesign of the flagship UI with glass-morphism and HTMX.",
        manager=admin,
        members=[alice, bob, charlie, elena, sara, marcus, jordan, leo, nadia],
        start=now - timedelta(days=30),
        end=now + timedelta(days=60),
        unit=Project.WORKLOAD_UNIT_STORY_POINTS,
        capacity_mode=Project.CAPACITY_MODE_PER_USER,
    )
    api2 = _build_project(
        code="API2",
        name="Backend API V2",
        description="RESTful API v2 with DRF, JWT auth, and full test coverage.",
        manager=leo,
        members=[alice, bob, charlie, elena, marcus],
        start=now - timedelta(days=15),
        end=now + timedelta(days=75),
        unit=Project.WORKLOAD_UNIT_STORY_POINTS,
        capacity_mode=Project.CAPACITY_MODE_GLOBAL,
    )
    mob = _build_project(
        code="MOB",
        name="Mobile App",
        description="Cross-platform mobile application planning phase.",
        manager=admin,
        members=[elena, sara, charlie, marcus],
        start=now + timedelta(days=7),
        end=now + timedelta(days=97),
        unit=Project.WORKLOAD_UNIT_MAN_HOURS,
        capacity_mode=Project.CAPACITY_MODE_GLOBAL,
    )
    return [qir, api2, mob]


def _build_project(code, name, description, manager, members, start, end, unit, capacity_mode):
    project, _ = Project.objects.get_or_create(
        code_prefix=code,
        defaults={
            "name": name,
            "description": description,
            "manager": manager,
            "start_date": start.date(),
            "end_date": end.date(),
            "workload_unit": unit,
            "capacity_mode": capacity_mode,
            "sprint_duration_days": SPRINT_DURATION_DAYS,
        },
    )
    ProjectMember.objects.get_or_create(project=project, user=manager, defaults={"role": "admin"})
    for user in members:
        ProjectMember.objects.get_or_create(project=project, user=user, defaults={"role": "member"})
    return project


# ── Story Points Schemes ─────────────────────────────────────────────────────

def create_story_points_schemes(projects):
    schemes = []
    for project in projects:
        scheme, _ = StoryPointsScheme.objects.get_or_create(
            project=project,
            defaults={"scheme_type": StoryPointsScheme.FIBONACCI},
        )
        schemes.append(scheme)
    return schemes


# ── Sprints ──────────────────────────────────────────────────────────────────

# Velocity data per closed sprint: list of (done_story_points, wip_story_points)
CLOSED_SPRINT_VELOCITY = [
    {"done": [5, 8, 3], "wip": [5]},          # 16 pts done, 40% consumption
    {"done": [5, 8, 5, 3], "wip": [8]},        # 21 pts done, 52.5%
    {"done": [8, 5, 3, 5, 8], "wip": [3]},     # 29 pts done, 72.5%
]

CLOSED_SPRINT_LABELS = ["a", "b", "c"]


def create_dataset_sprints(projects, users):
    admin = users[0]
    now = timezone.now()
    all_sprints = []

    for idx, project in enumerate(projects):
        closed = _create_closed_sprints(project, admin, idx, now)
        active, planned = _create_active_and_planned_sprints(project, admin, idx, now)
        all_sprints.extend(closed + [active, planned])

    return all_sprints


def _create_closed_sprints(project, admin, project_index, now):
    uses_global = project.capacity_mode == Project.CAPACITY_MODE_GLOBAL
    capacity = SPRINT_CAPACITY_POINTS if uses_global else None
    mode = Sprint.CAPACITY_MODE_GLOBAL if uses_global else Sprint.CAPACITY_MODE_PER_USER
    closed_sprints = []

    for i in range(CLOSED_SPRINT_COUNT):
        days_back = (CLOSED_SPRINT_COUNT - i) * CLOSED_SPRINT_GAP_DAYS + SPRINT_DURATION_DAYS
        start = (now - timedelta(days=days_back)).date()
        end = start + timedelta(days=CLOSED_SPRINT_GAP_DAYS - 1)
        label = CLOSED_SPRINT_LABELS[i]

        sprint, _ = Sprint.objects.get_or_create(
            project=project,
            name=f"Sprint {project_index + 1}.0{label}",
            defaults={
                "start_date": start,
                "end_date": end,
                "objective": f"Completed iteration {label} for {project.name}",
                "capacity": capacity,
                "status": Sprint.STATUS_CLOSED,
                "capacity_mode": mode,
                "created_by": admin,
                "closed_at": now - timedelta(days=(CLOSED_SPRINT_COUNT - i) * CLOSED_SPRINT_GAP_DAYS),
            },
        )
        closed_sprints.append(sprint)

    return closed_sprints


def _create_active_and_planned_sprints(project, admin, project_index, now):
    uses_global = project.capacity_mode == Project.CAPACITY_MODE_GLOBAL
    active_capacity = SPRINT_CAPACITY_POINTS if uses_global else None
    active_mode = Sprint.CAPACITY_MODE_GLOBAL if uses_global else Sprint.CAPACITY_MODE_PER_USER
    sprint_start = (now - timedelta(days=7)).date()

    active, _ = Sprint.objects.get_or_create(
        project=project,
        name=f"Sprint {project_index + 1}.1",
        defaults={
            "start_date": sprint_start,
            "end_date": sprint_start + timedelta(days=SPRINT_DURATION_DAYS - 1),
            "objective": f"Deliver core features for {project.name}",
            "capacity": active_capacity,
            "status": Sprint.STATUS_ACTIVE,
            "capacity_mode": active_mode,
            "created_by": admin,
        },
    )

    next_start = sprint_start + timedelta(days=SPRINT_DURATION_DAYS)
    planned, _ = Sprint.objects.get_or_create(
        project=project,
        name=f"Sprint {project_index + 1}.2",
        defaults={
            "start_date": next_start,
            "end_date": next_start + timedelta(days=SPRINT_DURATION_DAYS - 1),
            "objective": "Refinement, bug fixes, and polish.",
            "capacity": active_capacity,
            "status": Sprint.STATUS_PLANNED,
            "capacity_mode": active_mode,
            "created_by": admin,
        },
    )

    return active, planned


# ── Sprint User Capacities ───────────────────────────────────────────────────

def create_sprint_capacities(sprints, users):
    alice, bob, charlie, elena, sara, marcus = users[1], users[2], users[3], users[4], users[5], users[6]

    sprints_per_project = CLOSED_SPRINT_COUNT + 2
    qir_closed = sprints[0:CLOSED_SPRINT_COUNT]
    qir_active = sprints[CLOSED_SPRINT_COUNT]

    capacity_assignments = [
        (qir_active, alice,   12),
        (qir_active, bob,     10),
        (qir_active, charlie, 8),
        (qir_active, elena,   10),
    ]

    # Per-user capacity for QIR closed sprints (so consumption % computes)
    for closed_sprint in qir_closed:
        capacity_assignments.extend([
            (closed_sprint, alice,   12),
            (closed_sprint, bob,     10),
            (closed_sprint, charlie, 8),
            (closed_sprint, elena,   10),
        ])

    created = []
    for sprint, user, points in capacity_assignments:
        if sprint.capacity_mode != Sprint.CAPACITY_MODE_PER_USER:
            continue
        entry, _ = SprintUserCapacity.objects.get_or_create(
            sprint=sprint, user=user, defaults={"capacity": points}
        )
        created.append(entry)
    return created


# ── Tags ─────────────────────────────────────────────────────────────────────

def create_dataset_tags(projects):
    tags = []
    for project in projects:
        for label in TAG_LABELS:
            tag, _ = Tag.objects.get_or_create(name=label, project=project)
            tags.append(tag)
    return tags


# ── Tags by name helper ───────────────────────────────────────────────────────

def _tags_named(tags, project, *names):
    return [t for t in tags if t.project == project and t.name in names]


# ── Tickets ──────────────────────────────────────────────────────────────────

def create_dataset_tickets(projects, sprints, users, tags):
    admin, alice, bob, charlie, elena, sara, marcus, jordan = users[:8]

    qir, api2, mob = projects
    sprints_per_project = CLOSED_SPRINT_COUNT + 2

    qir_closed = sprints[0:CLOSED_SPRINT_COUNT]
    qir_active = sprints[CLOSED_SPRINT_COUNT]

    api_offset = sprints_per_project
    api_closed = sprints[api_offset:api_offset + CLOSED_SPRINT_COUNT]
    api_active = sprints[api_offset + CLOSED_SPRINT_COUNT]

    mob_offset = sprints_per_project * 2
    mob_closed = sprints[mob_offset:mob_offset + CLOSED_SPRINT_COUNT]
    mob_active = sprints[mob_offset + CLOSED_SPRINT_COUNT]

    qir_tickets = _create_qir_tickets(qir, qir_active, admin, alice, bob, elena, sara, marcus, tags)
    api_tickets = _create_api_tickets(api2, api_active, alice, bob, charlie, marcus, tags)
    mob_tickets = _create_mob_tickets(mob, mob_active, elena, sara, charlie, tags)

    closed_tickets = _create_all_closed_sprint_tickets(
        projects, [qir_closed, api_closed, mob_closed], users,
    )

    return qir_tickets + api_tickets + mob_tickets + closed_tickets


def _make_ticket(project, sprint, title, desc, issue_type, status, priority,
                 author, assignee=None, epic=None, sp=0, load=0,
                 color="#6B7FF0", order=0):
    return Ticket.objects.create(
        project=project, sprint=sprint,
        title=title, description=desc,
        issue_type=issue_type, status=status, priority=priority,
        author=author, assignee=assignee, epic=epic,
        story_points=sp, initial_load=load, remaining_load=load,
        color=color, backlog_order=order,
    )


def _create_qir_tickets(project, sprint, admin, alice, bob, elena, sara, marcus, tags):
    t = tags
    T, I, D = Ticket.STATUS_TODO, Ticket.STATUS_IN_PROGRESS, Ticket.STATUS_DONE

    epic_ui = _make_ticket(project, sprint, "UI Design System", "Establish component library", "EPIC", I, "HIGH", admin, color="#7C3AED", order=1)
    epic_ui.tags.set(_tags_named(t, project, "ui-ux", "frontend"))

    epic_infra = _make_ticket(project, None, "Infrastructure Modernisation", "Docker + CI/CD pipeline", "EPIC", T, "MEDIUM", admin, color="#059669", order=2)
    epic_infra.tags.set(_tags_named(t, project, "infrastructure", "backend"))

    s1 = _make_ticket(project, sprint, "Design token CSS variables", "Map all tokens in main.css", "STORY", D, "HIGH", elena, assignee=elena, epic=epic_ui, sp=5, load=5, order=3)
    s1.tags.set(_tags_named(t, project, "ui-ux", "frontend"))

    s2 = _make_ticket(project, sprint, "Glass-morphism card component", "Implement backdrop-blur card", "STORY", I, "HIGH", elena, assignee=sara, epic=epic_ui, sp=8, load=8, order=4)
    s2.tags.set(_tags_named(t, project, "ui-ux", "frontend"))

    s3 = _make_ticket(project, sprint, "Dark/Light theme toggle", "Persist preference in localStorage", "STORY", I, "MEDIUM", alice, assignee=alice, epic=epic_ui, sp=3, load=3, order=5)
    s3.tags.set(_tags_named(t, project, "frontend"))

    s4 = _make_ticket(project, sprint, "HTMX live ticket search", "Real-time search without full reload", "STORY", T, "MEDIUM", bob, assignee=bob, sp=8, load=8, order=6)
    s4.tags.set(_tags_named(t, project, "frontend", "backend"))

    s5 = _make_ticket(project, None, "Accessibility audit", "WCAG 2.1 AA compliance check", "STORY", T, "LOW", marcus, sp=5, load=5, order=7)
    s5.tags.set(_tags_named(t, project, "testing", "documentation"))

    b1 = _make_ticket(project, sprint, "Sidebar collapse flicker on Firefox", "Sidebar animation jank on resize", "BUG", I, "HIGH", alice, assignee=alice, order=8)
    b1.tags.set(_tags_named(t, project, "frontend"))

    b2 = _make_ticket(project, sprint, "Dark mode badge colour broken", "Badge uses hardcoded #fff in dark mode", "BUG", T, "MEDIUM", sara, assignee=sara, order=9)
    b2.tags.set(_tags_named(t, project, "ui-ux", "frontend"))

    b3 = _make_ticket(project, None, "Profile image upload fails", "JPEG > 2 MB causes 500 error", "BUG", T, "HIGH", marcus, order=10)
    b3.tags.set(_tags_named(t, project, "backend", "security"))

    task1 = _make_ticket(project, sprint, "Write CHANGELOG for v2", "Document all breaking changes", "TASK", I, "LOW", admin, assignee=alice, load=3, order=11)
    task1.tags.set(_tags_named(t, project, "documentation"))

    task2 = _make_ticket(project, sprint, "Docker Compose local dev setup", "Add docker-compose.yml with hot-reload", "TASK", T, "MEDIUM", bob, assignee=bob, epic=epic_infra, load=8, order=12)
    task2.tags.set(_tags_named(t, project, "infrastructure"))

    task3 = _make_ticket(project, None, "Add GitHub Actions CI pipeline", "Lint + test on every PR", "TASK", T, "HIGH", admin, epic=epic_infra, load=13, order=13)
    task3.tags.set(_tags_named(t, project, "infrastructure", "testing"))

    return [epic_ui, epic_infra, s1, s2, s3, s4, s5, b1, b2, b3, task1, task2, task3]


def _create_api_tickets(project, sprint, alice, bob, charlie, marcus, tags):
    t = tags
    T, I, D = Ticket.STATUS_TODO, Ticket.STATUS_IN_PROGRESS, Ticket.STATUS_DONE

    epic_auth = _make_ticket(project, sprint, "JWT Authentication System", "Access + refresh token flow", "EPIC", I, "HIGH", alice, color="#DC2626", order=1)
    epic_auth.tags.set(_tags_named(t, project, "backend", "security"))

    s1 = _make_ticket(project, sprint, "Token refresh endpoint", "POST /api/auth/refresh/", "STORY", D, "HIGH", alice, assignee=alice, epic=epic_auth, sp=5, load=5, order=2)
    s1.tags.set(_tags_named(t, project, "backend"))

    s2 = _make_ticket(project, sprint, "Permission middleware", "Role-based access on all routes", "STORY", I, "HIGH", bob, assignee=bob, epic=epic_auth, sp=8, load=8, order=3)
    s2.tags.set(_tags_named(t, project, "backend", "security"))

    s3 = _make_ticket(project, sprint, "OpenAPI schema generation", "drf-spectacular integration", "STORY", T, "MEDIUM", charlie, assignee=charlie, sp=3, load=3, order=4)
    s3.tags.set(_tags_named(t, project, "backend", "documentation"))

    s4 = _make_ticket(project, sprint, "Rate limiting on auth endpoints", "django-ratelimit on /login /refresh", "STORY", T, "HIGH", alice, assignee=alice, sp=5, load=5, order=5)
    s4.tags.set(_tags_named(t, project, "security", "backend"))

    s5 = _make_ticket(project, None, "Pagination helper mixin", "Cursor-based pagination for all list views", "STORY", T, "MEDIUM", bob, sp=5, load=5, order=6)
    s5.tags.set(_tags_named(t, project, "backend"))

    b1 = _make_ticket(project, sprint, "Token expiry not enforced on logout", "Blacklist not checked on logout", "BUG", I, "HIGH", marcus, assignee=marcus, epic=epic_auth, order=7)
    b1.tags.set(_tags_named(t, project, "security", "backend"))

    b2 = _make_ticket(project, sprint, "500 on nullable profile field", "Profile.bio raises AttributeError", "BUG", T, "MEDIUM", charlie, order=8)
    b2.tags.set(_tags_named(t, project, "backend"))

    b3 = _make_ticket(project, None, "N+1 query on ticket list endpoint", "select_related missing on assignee", "BUG", T, "HIGH", alice, order=9)
    b3.tags.set(_tags_named(t, project, "backend", "database"))

    task1 = _make_ticket(project, sprint, "Write DRF test suite", "Cover all ViewSets with pytest-django", "TASK", I, "HIGH", marcus, assignee=marcus, load=13, order=10)
    task1.tags.set(_tags_named(t, project, "testing"))

    task2 = _make_ticket(project, None, "Migrate to PostgreSQL locally", "Replace SQLite in dev docker-compose", "TASK", T, "MEDIUM", bob, load=5, order=11)
    task2.tags.set(_tags_named(t, project, "database", "infrastructure"))

    task3 = _make_ticket(project, None, "Add coverage badge to README", "codecov.io integration", "TASK", T, "LOW", charlie, load=2, order=12)
    task3.tags.set(_tags_named(t, project, "documentation", "testing"))

    return [epic_auth, s1, s2, s3, s4, s5, b1, b2, b3, task1, task2, task3]


def _create_mob_tickets(project, sprint, elena, sara, charlie, tags):
    t = tags
    T, I = Ticket.STATUS_TODO, Ticket.STATUS_IN_PROGRESS

    epic_ux = _make_ticket(project, sprint, "Mobile UX Foundation", "Core screens and navigation structure", "EPIC", I, "HIGH", elena, color="#0891B2", order=1)
    epic_ux.tags.set(_tags_named(t, project, "ui-ux", "frontend"))

    s1 = _make_ticket(project, sprint, "Onboarding flow screens", "4-step onboarding with skip logic", "STORY", T, "HIGH", elena, assignee=elena, epic=epic_ux, sp=8, load=8, order=2)
    s1.tags.set(_tags_named(t, project, "ui-ux"))

    s2 = _make_ticket(project, sprint, "Bottom navigation bar", "Tab bar with active state indicators", "STORY", T, "MEDIUM", sara, assignee=sara, epic=epic_ux, sp=5, load=5, order=3)
    s2.tags.set(_tags_named(t, project, "frontend", "ui-ux"))

    s3 = _make_ticket(project, None, "Push notification service", "Firebase FCM integration plan", "STORY", T, "MEDIUM", charlie, sp=13, load=13, order=4)
    s3.tags.set(_tags_named(t, project, "backend", "infrastructure"))

    s4 = _make_ticket(project, None, "Offline sync strategy", "Define conflict resolution approach", "STORY", T, "LOW", elena, sp=8, load=8, order=5)
    s4.tags.set(_tags_named(t, project, "backend", "documentation"))

    b1 = _make_ticket(project, sprint, "Layout breaks on small screens < 320px", "Flex overflow on tiny devices", "BUG", T, "HIGH", sara, order=6)
    b1.tags.set(_tags_named(t, project, "frontend", "ui-ux"))

    task1 = _make_ticket(project, sprint, "Write mobile design spec", "Figma handoff doc for all screens", "TASK", I, "MEDIUM", elena, assignee=elena, load=8, order=7)
    task1.tags.set(_tags_named(t, project, "documentation", "ui-ux"))

    task2 = _make_ticket(project, None, "Research React Native vs Flutter", "Technical feasibility report", "TASK", T, "HIGH", charlie, load=5, order=8)
    task2.tags.set(_tags_named(t, project, "documentation"))

    return [epic_ux, s1, s2, s3, s4, b1, task1, task2]


# ── Closed Sprint Tickets (statistics data) ──────────────────────────────────

CLOSED_SPRINT_STORY_TITLES = [
    "Setup project scaffolding",
    "Implement user authentication flow",
    "Build dashboard layout",
    "Add filtering and search",
    "Create data export feature",
    "Implement notification system",
    "Build settings page",
    "Add role-based permissions",
    "Create activity log module",
    "Implement caching layer",
    "Build analytics dashboard",
    "Add email integration",
    "Create batch processing pipeline",
    "Implement websocket updates",
    "Build reporting module",
    "Add audit trail",
    "Create onboarding wizard",
    "Implement file upload service",
]


def _create_all_closed_sprint_tickets(projects, closed_sprints_per_project, users):
    admin = users[0]
    all_tickets = []
    title_offset = 0

    for project, closed_sprints in zip(projects, closed_sprints_per_project):
        members = _get_project_assignees(project, users)
        for sprint_index, sprint in enumerate(closed_sprints):
            velocity = CLOSED_SPRINT_VELOCITY[sprint_index]
            tickets = _create_single_closed_sprint_tickets(
                project, sprint, admin, members,
                velocity["done"], velocity["wip"], title_offset,
            )
            all_tickets.extend(tickets)
            title_offset += len(velocity["done"]) + len(velocity["wip"])

    return all_tickets


def _get_project_assignees(project, users):
    member_ids = set(
        project.members.values_list("user_id", flat=True)
    )
    return [u for u in users if u.id in member_ids and not u.is_staff]


def _create_single_closed_sprint_tickets(project, sprint, admin, members, done_points, wip_points, title_offset):
    D = Ticket.STATUS_DONE
    I = Ticket.STATUS_IN_PROGRESS
    tickets = []
    order = 1

    for idx, story_points in enumerate(done_points):
        assignee = members[idx % len(members)] if members else admin
        title_index = (title_offset + idx) % len(CLOSED_SPRINT_STORY_TITLES)
        ticket = _make_ticket(
            project, sprint,
            f"{CLOSED_SPRINT_STORY_TITLES[title_index]} ({sprint.name})",
            f"Completed in {sprint.name}",
            "STORY", D, "MEDIUM", admin,
            assignee=assignee, sp=story_points, load=story_points, order=order,
        )
        tickets.append(ticket)
        order += 1

    for idx, story_points in enumerate(wip_points):
        assignee = members[(len(done_points) + idx) % len(members)] if members else admin
        title_index = (title_offset + len(done_points) + idx) % len(CLOSED_SPRINT_STORY_TITLES)
        ticket = _make_ticket(
            project, sprint,
            f"{CLOSED_SPRINT_STORY_TITLES[title_index]} ({sprint.name})",
            f"Carried over from {sprint.name}",
            "STORY", I, "HIGH", admin,
            assignee=assignee, sp=story_points, load=story_points, order=order,
        )
        tickets.append(ticket)
        order += 1

    return tickets


# ── Ticket Links ─────────────────────────────────────────────────────────────

def create_ticket_links(project_tickets_map):
    created = []
    for tickets in project_tickets_map.values():
        _add_links_within_project(tickets, created)
    return created


def _add_links_within_project(tickets, created):
    stories = [t for t in tickets if t.issue_type == "STORY"]
    bugs    = [t for t in tickets if t.issue_type == "BUG"]
    tasks   = [t for t in tickets if t.issue_type == "TASK"]

    link_pairs = []
    if len(stories) >= 2:
        link_pairs.append((stories[0], stories[1], TicketLink.TYPE_RELATES_TO))
    if len(stories) >= 4:
        link_pairs.append((stories[2], stories[3], TicketLink.TYPE_RELATES_TO))
    if stories and bugs:
        link_pairs.append((bugs[0], stories[0], TicketLink.TYPE_BLOCKED_BY))
    if len(bugs) >= 2 and stories:
        link_pairs.append((bugs[1], stories[0], TicketLink.TYPE_RELATES_TO))
    if tasks and stories:
        link_pairs.append((tasks[0], stories[0], TicketLink.TYPE_BLOCKED_BY))
    if len(tasks) >= 2 and len(stories) >= 2:
        link_pairs.append((tasks[1], stories[1], TicketLink.TYPE_RELATES_TO))

    for src, tgt, link_type in link_pairs:
        link = _safe_create_link(src, tgt, link_type)
        if link:
            created.append(link)


def _safe_create_link(source, target, link_type):
    try:
        link, created = TicketLink.objects.get_or_create(
            source_ticket=source,
            target_ticket=target,
            link_type=link_type,
        )
        return link if created else None
    except Exception:
        return None


# ── Ticket Attachments ───────────────────────────────────────────────────────

def create_ticket_attachments(tickets_with_attachments):
    created = []
    for ticket in tickets_with_attachments:
        attachment = TicketAttachment(ticket=ticket)
        png_bytes = _minimal_png(ticket.id)
        attachment.file.save(
            f"attachment_ticket_{ticket.id}.png",
            ContentFile(png_bytes),
            save=True,
        )
        created.append(attachment)
    return created


def _minimal_png(seed):
    """Generate a deterministic 1×1 PNG using pure Python (no external deps)."""
    r = (seed * 47 + 3) % 256
    g = (seed * 97 + 7) % 256
    b = (seed * 137 + 11) % 256
    raw = struct.pack(">BBBBBBBB", 0, r, g, b, 255, r, g, b)
    compressed = zlib.compress(raw)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )
    return png


def _png_chunk(chunk_type, data):
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


# ── Git Repositories ─────────────────────────────────────────────────────────

def create_git_repositories(qir_project, api_project):
    repos = []
    qir_repo, _ = GitRepository.objects.get_or_create(
        project=qir_project,
        defaults={
            "repository_url": "https://github.com/jiren-demo/quantum-interface",
            "repository_type": GitRepository.REPOSITORY_TYPE_GITHUB,
            "is_private": False,
        },
    )
    repos.append(qir_repo)

    api_repo, _ = GitRepository.objects.get_or_create(
        project=api_project,
        defaults={
            "repository_url": "https://gitlab.com/jiren-demo/backend-api-v2",
            "repository_type": GitRepository.REPOSITORY_TYPE_GITLAB,
            "is_private": True,
            "access_token": "glpat-test-placeholder-token",
        },
    )
    repos.append(api_repo)
    return repos
