import django.contrib.auth.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_alter_invitation_role_assigned_alter_profile_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="invitation",
            name="username",
            field=models.CharField(
                default="",
                help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                max_length=150,
                validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="invitation",
            constraint=models.UniqueConstraint(
                condition=models.Q(used=False),
                fields=("username",),
                name="unique_pending_invitation_username",
            ),
        ),
    ]
