from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = 'Add a user to the Managers group'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to add to Managers group')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User "{username}" not found')
            )
            return

        # Get or create Managers group
        managers_group, created = Group.objects.get_or_create(name='Managers')
        if created:
            self.stdout.write(
                self.style.WARNING('ℹ️  Created Managers group (it didn\'t exist)')
            )

        # Check if user already has dataset creation permissions
        if user.is_superuser or user.is_staff:
            self.stdout.write(
                self.style.WARNING(f'ℹ️  User "{username}" is already a superuser/staff - can already create datasets!')
            )
        elif user.groups.filter(name='Managers').exists():
            self.stdout.write(
                self.style.WARNING(f'ℹ️  User "{username}" is already in Managers group')
            )
        else:
            user.groups.add(managers_group)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Added "{username}" to Managers group - can now create datasets!')
            )
