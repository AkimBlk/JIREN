from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_profile_role_invitation'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitation',
            name='role_assigned',
            field=models.CharField(
                choices=[
                    ('admin', 'Product Owner (Admin)'),
                    ('contributeur', 'Scrum Master (Contributeur)'),
                    ('read-only', 'Developer (Read-Only)'),
                ],
                default='read-only',
                max_length=20,
            ),
        ),
    ]
