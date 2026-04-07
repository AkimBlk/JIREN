from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

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
        User = get_user_model()

        def create_admin():
            admin_user, created = User.objects.get_or_create(
                username="admintest",
                defaults={
                    "email": "admin@jiren.com",
                }
            )
            admin_user.email = "admin@jiren.com"
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.set_password("admin123")
            admin_user.save()

            if created:
                self.stdout.write(
                    self.style.SUCCESS("Admin user created (admintest / admin123)")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("Admin user updated (admintest / admin123)")
                )

        if options["clean"]:
            clear_test_dataset()
            self.stdout.write(self.style.WARNING("Cleared existing test dataset."))

        users = create_dataset_users()
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(users)} users"))

        projects = create_dataset_projects(users)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(projects)} projects"))

        schemes = create_story_points_schemes(projects)
        self.stdout.write(
            self.style.SUCCESS(f"[OK] {len(schemes)} story-points schemes (Fibonacci)")
        )

        sprints = create_dataset_sprints(projects, users)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(sprints)} sprints"))

        capacities = create_sprint_capacities(sprints, users)
        self.stdout.write(
            self.style.SUCCESS(f"[OK] {len(capacities)} sprint user-capacity records")
        )

        tags = create_dataset_tags(projects)
        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] {len(tags)} tags ({len(tags) // len(projects)} per project)"
            )
        )

        all_tickets = create_dataset_tickets(projects, sprints, users, tags)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(all_tickets)} tickets"))

        project_tickets_map = {
            projects[0]: [t for t in all_tickets if t.project == projects[0]],
            projects[1]: [t for t in all_tickets if t.project == projects[1]],
            projects[2]: [t for t in all_tickets if t.project == projects[2]],
        }
        links = create_ticket_links(project_tickets_map)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(links)} ticket links"))

        attachment_tickets = [
            all_tickets[i]
            for i in ATTACHMENT_TICKET_INDICES
            if i < len(all_tickets)
        ]
        attachments = create_ticket_attachments(attachment_tickets)
        self.stdout.write(
            self.style.SUCCESS(f"[OK] {len(attachments)} ticket attachments")
        )

        repos = create_git_repositories(projects[0], projects[1])
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(repos)} git repositories"))

        create_admin()

        self._print_summary(
            users,
            projects,
            sprints,
            all_tickets,
            tags,
            links,
            attachments,
        )

    def _print_summary(self, users, projects, sprints, tickets, tags, links, attachments):
        self.stdout.write("\n" + "━" * 50)
        self.stdout.write(self.style.HTTP_INFO("TEST DATASET SUMMARY"))
        self.stdout.write("━" * 50)
        self.stdout.write(f"  Users        : {len(users)}")
        self.stdout.write(f"  Projects     : {len(projects)}")

        closed = sum(1 for s in sprints if s.status == "CLOSED")
        active = sum(1 for s in sprints if s.status == "ACTIVE")
        planned = sum(1 for s in sprints if s.status == "PLANNED")
        self.stdout.write(
            f"  Sprints      : {len(sprints)} ({closed} closed, {active} active, {planned} planned)"
        )

        self.stdout.write(f"  Tickets      : {len(tickets)}")
        epics = sum(1 for t in tickets if t.issue_type == "EPIC")
        stories = sum(1 for t in tickets if t.issue_type == "STORY")
        bugs = sum(1 for t in tickets if t.issue_type == "BUG")
        tasks = sum(1 for t in tickets if t.issue_type == "TASK")
        self.stdout.write(f"    EPIC {epics}  STORY {stories}  BUG {bugs}  TASK {tasks}")

        self.stdout.write(f"  Tags         : {len(tags)}")
        self.stdout.write(f"  Links        : {len(links)}")
        self.stdout.write(f"  Attachments  : {len(attachments)}")
        self.stdout.write("━" * 50)
        self.stdout.write(self.style.SUCCESS("Dataset ready."))
        self.stdout.write("Admin login: admintest / admin123")
        self.stdout.write("Test users password: testpass123")