from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Create default groups for the application'

    def handle(self, *args, **options):
        # Create Managers group
        managers_group, created = Group.objects.get_or_create(name='Managers')
        if created:
            self.stdout.write(
                self.style.SUCCESS('✅ Created Managers group')
            )
        else:
            self.stdout.write(
                self.style.WARNING('ℹ️  Managers group already exists')
            )

        # You can add more groups here in the future
        # Example:
        # editors_group, created = Group.objects.get_or_create(name='Editors')
        # if created:
        #     self.stdout.write(self.style.SUCCESS('✅ Created Editors group'))

        self.stdout.write(
            self.style.SUCCESS('🎉 Group setup completed!')
        )
