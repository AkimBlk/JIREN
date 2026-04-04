from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from blog.models import Project, ProjectMember, Sprint, Tag, Ticket, TicketLink

DEMO_USERS = [
    {"username": "demo_chef_projet", "email": "chef@demo.com", "first_name": "Alice", "last_name": "Manager"},
    {"username": "demo_dev_senior", "email": "senior@demo.com", "first_name": "Bob", "last_name": "Developer"},
    {"username": "demo_dev_junior", "email": "junior@demo.com", "first_name": "Charlie", "last_name": "Dev"},
    {"username": "demo_tester", "email": "qaa@demo.com", "first_name": "Diana", "last_name": "QA"},
    {"username": "demo_designer", "email": "design@demo.com", "first_name": "Eve", "last_name": "Designer"},
    {"username": "demo_devops", "email": "devops@demo.com", "first_name": "Frank", "last_name": "DevOps"},
]

TAG_NAMES = [
    "backend", "frontend", "bug", "feature",
    "performance", "security", "documentation", "testing",
]


def clear_demo_data():
    User.objects.filter(username__startswith="demo_").delete()
    Project.objects.all().delete()
    Sprint.objects.all().delete()
    Ticket.objects.all().delete()
    Tag.objects.all().delete()


def create_users():
    users = []
    for data in DEMO_USERS:
        user, _ = User.objects.get_or_create(
            username=data["username"],
            defaults={k: v for k, v in data.items() if k != "username"},
        )
        users.append(user)
    return users


def create_projects(users):
    chef, senior_dev, junior_dev, tester, designer, devops = users

    proj_crm = _create_project("CRM", "CRM System", chef, [chef, senior_dev, junior_dev, tester])
    proj_ecom = _create_project("ECOM", "E-Commerce Platform", senior_dev, [senior_dev, junior_dev, designer, devops])
    proj_mobile = _create_project("MOBILE", "Mobile App", designer, [designer, senior_dev, tester])

    return [proj_crm, proj_ecom, proj_mobile]


def _create_project(code, name, manager, members):
    now = timezone.now()
    project, _ = Project.objects.get_or_create(
        code_prefix=code,
        defaults={
            "name": name,
            "description": f"{name} demo project",
            "manager": manager,
            "start_date": (now - timedelta(days=30)).date(),
            "end_date": (now + timedelta(days=90)).date(),
            "workload_unit": Project.WORKLOAD_UNIT_STORY_POINTS,
            "capacity_mode": Project.CAPACITY_MODE_PER_USER,
            "sprint_duration_days": 14,
        },
    )
    for user in members:
        role = "admin" if user == manager else "member"
        ProjectMember.objects.get_or_create(project=project, user=user, defaults={"role": role})
    return project


def create_sprints(projects):
    sprints = []
    now = timezone.now()
    sprint_start = now.date() - timedelta(days=now.weekday())

    for idx, project in enumerate(projects):
        active, _ = Sprint.objects.get_or_create(
            project=project,
            name=f"Sprint {idx + 1}.1 - Current",
            defaults={
                "start_date": sprint_start,
                "end_date": sprint_start + timedelta(days=project.sprint_duration_days - 1),
                "objective": f"Core features for {project.name}",
                "capacity": 40,
                "status": Sprint.STATUS_ACTIVE,
                "capacity_mode": Sprint.CAPACITY_MODE_GLOBAL,
            },
        )
        sprints.append(active)

        next_start = sprint_start + timedelta(days=project.sprint_duration_days)
        planned, _ = Sprint.objects.get_or_create(
            project=project,
            name=f"Sprint {idx + 1}.2 - Upcoming",
            defaults={
                "start_date": next_start,
                "end_date": next_start + timedelta(days=project.sprint_duration_days - 1),
                "objective": "Refinement and optimization phase",
                "capacity": 40,
                "status": Sprint.STATUS_PLANNED,
                "capacity_mode": Sprint.CAPACITY_MODE_GLOBAL,
            },
        )
        sprints.append(planned)

    return sprints


def create_tags(projects):
    tags = []
    for project in projects:
        for name in TAG_NAMES:
            tag, _ = Tag.objects.get_or_create(name=name, project=project)
            tags.append(tag)
    return tags


def create_tickets(projects, sprints, users, tags):
    chef, senior_dev = users[0], users[1]
    crm_tags = [t for t in tags if t.project == projects[0]]
    ecom_tags = [t for t in tags if t.project == projects[1]]
    mobile_tags = [t for t in tags if t.project == projects[2]]

    crm_tickets = _create_crm_tickets(projects[0], sprints[0], sprints[1], chef, crm_tags)
    ecom_tickets = _create_ecom_tickets(projects[1], sprints[2], users[2], ecom_tags)
    mobile_tickets = _create_mobile_tickets(projects[2], sprints[4], users[4], mobile_tags)

    return crm_tickets + ecom_tickets + mobile_tickets


def _create_crm_tickets(project, current_sprint, next_sprint, chef, tags):
    tickets = []

    epic_ums = Ticket.objects.create(
        project=project, sprint=current_sprint,
        title="User Management System",
        description="Complete user authentication, roles, and permissions framework",
        issue_type=Ticket.ISSUE_TYPE_EPIC, priority="HIGH",
        status=Ticket.STATUS_IN_PROGRESS, author=chef, color="#FF6B6B",
    )
    epic_ums.tags.set([t for t in tags if t.name in ["backend", "security", "feature"]])
    tickets.append(epic_ums)

    story1 = Ticket.objects.create(
        project=project, sprint=current_sprint,
        title="Implement user registration",
        description="Create registration form with email validation",
        issue_type=Ticket.ISSUE_TYPE_STORY, epic=epic_ums,
        priority="HIGH", story_points=5, status=Ticket.STATUS_DONE, author=chef,
    )
    story1.tags.set([t for t in tags if t.name in ["frontend", "feature"]])
    tickets.append(story1)

    story2 = Ticket.objects.create(
        project=project, sprint=current_sprint,
        title="Implement password reset flow",
        description="Add secure password reset with email verification",
        issue_type=Ticket.ISSUE_TYPE_STORY, epic=epic_ums,
        priority="HIGH", story_points=3, status=Ticket.STATUS_IN_PROGRESS, author=chef,
    )
    story2.tags.set([t for t in tags if t.name in ["frontend", "security"]])
    tickets.append(story2)

    task1 = Ticket.objects.create(
        project=project, sprint=current_sprint,
        title="Setup OAuth2 integration",
        description="Configure OAuth2 with Google and Microsoft",
        issue_type=Ticket.ISSUE_TYPE_TASK, epic=epic_ums,
        priority="MEDIUM", status=Ticket.STATUS_TODO, author=chef,
    )
    task1.tags.set([t for t in tags if t.name in ["backend", "feature"]])
    tickets.append(task1)

    epic_dashboard = Ticket.objects.create(
        project=project, sprint=next_sprint,
        title="Dashboard & Analytics",
        description="Real-time analytics dashboard with charts and KPIs",
        issue_type=Ticket.ISSUE_TYPE_EPIC, priority="HIGH",
        status=Ticket.STATUS_TODO, author=chef, color="#4ECDC4",
    )
    epic_dashboard.tags.set([t for t in tags if t.name in ["frontend", "feature"]])
    tickets.append(epic_dashboard)

    return tickets


def _create_ecom_tickets(project, sprint, author, tags):
    tickets = []

    epic_payment = Ticket.objects.create(
        project=project, sprint=sprint,
        title="Payment Integration",
        description="Integrate Stripe, PayPal, and other payment gateways",
        issue_type=Ticket.ISSUE_TYPE_EPIC, priority="HIGH",
        status=Ticket.STATUS_IN_PROGRESS, author=author, color="#FFE66D",
    )
    epic_payment.tags.set([t for t in tags if t.name in ["backend", "security", "feature"]])
    tickets.append(epic_payment)

    story_payment = Ticket.objects.create(
        project=project, sprint=sprint,
        title="Implement Stripe checkout",
        description="Create secure Stripe payment checkout flow",
        issue_type=Ticket.ISSUE_TYPE_STORY, epic=epic_payment,
        priority="HIGH", story_points=13,
        status=Ticket.STATUS_IN_PROGRESS, author=author,
    )
    story_payment.tags.set([t for t in tags if t.name in ["backend", "feature", "testing"]])
    tickets.append(story_payment)

    bug1 = Ticket.objects.create(
        project=project, sprint=sprint,
        title="Fix payment timeout issue",
        description="Payment processing times out after 30 seconds",
        issue_type=Ticket.ISSUE_TYPE_BUG, epic=epic_payment,
        priority="HIGH", status=Ticket.STATUS_IN_PROGRESS, author=author,
    )
    bug1.tags.set([t for t in tags if t.name in ["backend", "bug", "performance"]])
    tickets.append(bug1)

    return tickets


def _create_mobile_tickets(project, sprint, author, tags):
    epic_ui = Ticket.objects.create(
        project=project, sprint=sprint,
        title="Mobile UI Framework",
        description="Build reusable mobile UI components and design system",
        issue_type=Ticket.ISSUE_TYPE_EPIC, priority="HIGH",
        status=Ticket.STATUS_TODO, author=author, color="#A8E6CF",
    )
    epic_ui.tags.set([t for t in tags if t.name in ["frontend", "feature", "documentation"]])
    return [epic_ui]


def create_ticket_links(tickets):
    if len(tickets) < 4:
        return []

    links = []
    story1, story2, _, task1 = tickets[0], tickets[1], tickets[2], tickets[3]

    link = _safe_create_link(task1, story1, TicketLink.TYPE_BLOCKED_BY)
    if link:
        links.append(link)

    link = _safe_create_link(story2, story1, TicketLink.TYPE_RELATES_TO)
    if link:
        links.append(link)

    if len(tickets) >= 8:
        epic_payment, story_payment, bug1 = tickets[5], tickets[6], tickets[7]
        link = _safe_create_link(story_payment, bug1, TicketLink.TYPE_BLOCKED_BY)
        if link:
            links.append(link)

    return links


def _safe_create_link(source, target, link_type):
    try:
        return TicketLink.objects.create(
            source_ticket=source, target_ticket=target, link_type=link_type
        )
    except Exception:
        return None
