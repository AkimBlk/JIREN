from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Profile


class Command(BaseCommand):
    help = 'Create missing Profile objects for existing users'

    def handle(self, *args, **options):
        created_list = []
        for user in User.objects.all():
            _, created = Profile.objects.get_or_create(user=user)
            if created:
                created_list.append(user.username)
        if created_list:
            self.stdout.write(self.style.SUCCESS(f'Profiles created for: {", ".join(created_list)}'))
        else:
            self.stdout.write(self.style.SUCCESS('All users already have profiles.'))
