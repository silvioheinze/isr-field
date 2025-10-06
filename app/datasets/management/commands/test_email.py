from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            help='Email address to send test email to',
            required=True
        )

    def handle(self, *args, **options):
        to_email = options['to']
        
        self.stdout.write(f"Testing email configuration...")
        self.stdout.write(f"Email backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Email host: {settings.EMAIL_HOST}")
        self.stdout.write(f"Email port: {settings.EMAIL_PORT}")
        self.stdout.write(f"TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"SSL: {settings.EMAIL_USE_SSL}")
        self.stdout.write(f"From email: {settings.DEFAULT_FROM_EMAIL}")
        
        try:
            send_mail(
                subject='Test Email from ISR Field',
                message='This is a test email to verify SMTP configuration is working correctly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS(f'Test email sent successfully to {to_email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to send test email: {str(e)}')
            )
