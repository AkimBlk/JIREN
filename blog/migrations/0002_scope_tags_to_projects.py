# Generated manually to restore migration parity with the current Tag model.

from django.db import migrations, models
import django.db.models.deletion


def assign_projects_to_existing_tags(apps, schema_editor):
    Tag = apps.get_model("blog", "Tag")
    Ticket = apps.get_model("blog", "Ticket")
    TagAssignment = Ticket.tags.through

    for tag in Tag.objects.all().order_by("id"):
        ticket_ids = list(
            TagAssignment.objects.filter(tag_id=tag.id).values_list("ticket_id", flat=True)
        )
        project_ids = list(
            Ticket.objects.filter(id__in=ticket_ids)
            .order_by("project_id")
            .values_list("project_id", flat=True)
            .distinct()
        )

        if not project_ids:
            tag.delete()
            continue

        tag.project_id = project_ids[0]
        tag.save(update_fields=["project"])

        for project_id in project_ids[1:]:
            duplicate_tag = Tag.objects.create(
                project_id=project_id,
                name=tag.name,
                normalized_name=tag.normalized_name,
            )
            project_ticket_ids = list(
                Ticket.objects.filter(id__in=ticket_ids, project_id=project_id).values_list("id", flat=True)
            )
            TagAssignment.objects.filter(
                tag_id=tag.id,
                ticket_id__in=project_ticket_ids,
            ).update(tag_id=duplicate_tag.id)


def remove_project_scope_from_tags(apps, schema_editor):
    Tag = apps.get_model("blog", "Tag")
    Ticket = apps.get_model("blog", "Ticket")
    TagAssignment = Ticket.tags.through

    normalized_to_tag_id = {}
    duplicate_tag_ids = []

    for tag in Tag.objects.all().order_by("id"):
        canonical_tag_id = normalized_to_tag_id.get(tag.normalized_name)
        if canonical_tag_id is None:
            normalized_to_tag_id[tag.normalized_name] = tag.id
            continue

        TagAssignment.objects.filter(tag_id=tag.id).update(tag_id=canonical_tag_id)
        duplicate_tag_ids.append(tag.id)

    if duplicate_tag_ids:
        Tag.objects.filter(id__in=duplicate_tag_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0001_squashed_0020_ticketlink_ticketlink_unique_ticket_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="project",
            field=models.ForeignKey(
                blank=True,
                help_text="The project this tag belongs to.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tags",
                to="blog.project",
            ),
        ),
        migrations.RunPython(
            assign_projects_to_existing_tags,
            remove_project_scope_from_tags,
        ),
        migrations.AlterField(
            model_name="tag",
            name="normalized_name",
            field=models.CharField(editable=False, max_length=50),
        ),
        migrations.AlterField(
            model_name="tag",
            name="project",
            field=models.ForeignKey(
                help_text="The project this tag belongs to.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tags",
                to="blog.project",
            ),
        ),
        migrations.AddConstraint(
            model_name="tag",
            constraint=models.UniqueConstraint(
                fields=("project", "normalized_name"),
                name="unique_tag_per_project",
            ),
        ),
    ]
