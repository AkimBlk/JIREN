"""
Management command: create_test_dataset

Creates a comprehensive dataset that exercises every feature of the site:
  - 10 users (admin, devs, designers, QA, product)
  - 3 projects (story-points/per-user, story-points/global, man-hours/global)
  - 15 sprints (3 closed + 1 active + 1 planned per project)
  - 33+ active tickets + ~36 closed sprint tickets (EPIC, STORY, BUG, TASK)
  - 8 tags per project (infrastructure, frontend, backend, …)
  - 15+ ticket links (BLOCKED_BY and RELATES_TO within each project)
  - 5+ ticket attachments (minimal PNG files)
  - StoryPointsScheme (Fibonacci) for each project
  - GitRepository (GitHub + GitLab) for 2 projects
  - SprintUserCapacity for per-user capacity sprints

Usage:
  python manage.py create_test_dataset
  python manage.py create_test_dataset --clean
"""
from django.core.management.base import BaseCommand

from .test_dataset_creators import (
    clear_test_dataset,
    create_dataset_projects,
    create_dataset_sprints,
    create_dataset_tags,
    create_dataset_tickets,
    create_dataset_users,
    create_git_repositories,
    create_sprint_capacities,
    create_story_points_schemes,
    create_ticket_attachments,
    create_ticket_links,
)

ATTACHMENT_TICKET_INDICES = [0, 2, 4, 6, 8]


class Command(BaseCommand):
    help = "Populate database with comprehensive test dataset covering all site features"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete existing test dataset before creating a fresh one.",
        )

    def handle(self, *args, **options):
        if options["clean"]:
            clear_test_dataset()
            self.stdout.write(self.style.WARNING("Cleared existing test dataset."))

        users = create_dataset_users()
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(users)} users"))

        projects = create_dataset_projects(users)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(projects)} projects"))

        schemes = create_story_points_schemes(projects)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(schemes)} story-points schemes (Fibonacci)"))

        sprints = create_dataset_sprints(projects, users)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(sprints)} sprints"))

        capacities = create_sprint_capacities(sprints, users)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(capacities)} sprint user-capacity records"))

        tags = create_dataset_tags(projects)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(tags)} tags ({len(tags) // len(projects)} per project)"))

        all_tickets = create_dataset_tickets(projects, sprints, users, tags)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(all_tickets)} tickets"))

        project_tickets_map = {
            projects[0]: [t for t in all_tickets if t.project == projects[0]],
            projects[1]: [t for t in all_tickets if t.project == projects[1]],
            projects[2]: [t for t in all_tickets if t.project == projects[2]],
        }
        links = create_ticket_links(project_tickets_map)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(links)} ticket links"))

        attachment_tickets = [all_tickets[i] for i in ATTACHMENT_TICKET_INDICES if i < len(all_tickets)]
        attachments = create_ticket_attachments(attachment_tickets)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(attachments)} ticket attachments"))

        repos = create_git_repositories(projects[0], projects[1])
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(repos)} git repositories"))

        self._print_summary(users, projects, sprints, all_tickets, tags, links, attachments)

    def _print_summary(self, users, projects, sprints, tickets, tags, links, attachments):
        self.stdout.write("\n" + "━" * 50)
        self.stdout.write(self.style.HTTP_INFO("TEST DATASET SUMMARY"))
        self.stdout.write("━" * 50)
        self.stdout.write(f"  Users        : {len(users)}")
        self.stdout.write(f"  Projects     : {len(projects)}")
        closed  = sum(1 for s in sprints if s.status == "CLOSED")
        active  = sum(1 for s in sprints if s.status == "ACTIVE")
        planned = sum(1 for s in sprints if s.status == "PLANNED")
        self.stdout.write(f"  Sprints      : {len(sprints)} ({closed} closed, {active} active, {planned} planned)")
        self.stdout.write(f"  Tickets      : {len(tickets)}")
        epics   = sum(1 for t in tickets if t.issue_type == "EPIC")
        stories = sum(1 for t in tickets if t.issue_type == "STORY")
        bugs    = sum(1 for t in tickets if t.issue_type == "BUG")
        tasks   = sum(1 for t in tickets if t.issue_type == "TASK")
        self.stdout.write(f"    EPIC {epics}  STORY {stories}  BUG {bugs}  TASK {tasks}")
        self.stdout.write(f"  Tags         : {len(tags)}")
        self.stdout.write(f"  Links        : {len(links)}")
        self.stdout.write(f"  Attachments  : {len(attachments)}")
        self.stdout.write("━" * 50)
        self.stdout.write(self.style.SUCCESS("Dataset ready. Login: testpass123 for all users."))
