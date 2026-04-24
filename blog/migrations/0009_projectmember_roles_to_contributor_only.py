from django.db import migrations, models


LEGACY_ROLE_VALUES = ("admin", "member", "read_only", "read-only")


def normalize_project_member_roles_forward(apps, _schema_editor):
    ProjectMember = apps.get_model("blog", "ProjectMember")
    ProjectMember.objects.filter(role__in=LEGACY_ROLE_VALUES).update(role="contributor")


def normalize_project_member_roles_reverse(apps, _schema_editor):
    # Keep contributor values on rollback to avoid reintroducing deprecated roles.
    return


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0008_ticket_linked_commit_url"),
    ]

    operations = [
        migrations.RunPython(
            normalize_project_member_roles_forward,
            normalize_project_member_roles_reverse,
        ),
        migrations.AlterField(
            model_name="projectmember",
            name="role",
            field=models.CharField(
                choices=[("contributor", "Contributor")],
                default="contributor",
                max_length=20,
            ),
        ),
    ]
