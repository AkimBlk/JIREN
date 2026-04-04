from django.core.management.base import BaseCommand

from blog.models import Ticket, TicketLink
from .demo_data_creators import (
    clear_demo_data,
    create_projects,
    create_sprints,
    create_tags,
    create_tickets,
    create_users,
    _safe_create_link,
)

MIN_TICKETS_FOR_LINKS = 6


class Command(BaseCommand):
    help = "Populate database with professional demo data for testing"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before populating")

    def handle(self, *args, **options):
        if options["clear"]:
            clear_demo_data()
            self.stdout.write(self.style.WARNING("[WARN] Cleared existing demo data"))

        users = create_users()
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(users)} demo users"))

        projects = create_projects(users)
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(projects)} projects"))

        sprints = create_sprints(projects)
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(sprints)} sprints"))

        tags = create_tags(projects)
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(tags)} tags"))

        tickets = create_tickets(projects, sprints, users, tags)
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(tickets)} tickets/epics"))

        links = self.create_ticket_links(tickets)
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(links)} ticket links"))

        self._print_summary(users, projects, tickets, tags, links)

    def create_ticket_links(self, tickets):
        if len(tickets) < MIN_TICKETS_FOR_LINKS:
            return []

        t0, t1, t2, t3, t4, t5 = tickets[:6]
        candidates = [
            (t3, t0, TicketLink.TYPE_BLOCKED_BY),
            (t4, t1, TicketLink.TYPE_BLOCKED_BY),
            (t1, t0, TicketLink.TYPE_RELATES_TO),
            (t5, t2, TicketLink.TYPE_RELATES_TO),
        ]
        return [
            link
            for source, target, link_type in candidates
            if (link := _safe_create_link(source, target, link_type))
        ]

    def _print_summary(self, users, projects, tickets, tags, links):
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("[SUCCESS] DEMO DATA SUCCESSFULLY POPULATED"))
        self.stdout.write("=" * 70 + "\n")

        self.stdout.write(self.style.WARNING("[USERS CREATED]"))
        for user in users:
            self.stdout.write(f"   - {user.get_full_name()} ({user.username})")

        self.stdout.write(self.style.WARNING("\n[PROJECTS CREATED]"))
        for project in projects:
            self.stdout.write(f"   - [{project.code_prefix}] {project.name} ({project.members.count()} members)")

        self.stdout.write(self.style.WARNING("\n[TICKETS CREATED]"))
        epics = [t for t in tickets if t.issue_type == Ticket.ISSUE_TYPE_EPIC]
        stories = [t for t in tickets if t.issue_type == Ticket.ISSUE_TYPE_STORY]
        tasks = [t for t in tickets if t.issue_type == Ticket.ISSUE_TYPE_TASK]
        bugs = [t for t in tickets if t.issue_type == Ticket.ISSUE_TYPE_BUG]
        self.stdout.write(f"   - {len(epics)} Epics, {len(stories)} Stories, {len(tasks)} Tasks, {len(bugs)} Bugs")

        self.stdout.write(self.style.WARNING("\n[RELATIONSHIPS]"))
        self.stdout.write(f"   - {len(links)} Ticket links, {len(tags)} Tags")

        self.stdout.write(self.style.SUCCESS("\n[READY FOR TESTING]"))
        self.stdout.write("   Login with any demo_* user (no password required in dev mode)")
        self.stdout.write("=" * 70 + "\n")
