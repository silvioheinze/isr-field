from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


class CreateUserViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin)
        self.url = reverse('create_user')

    def test_form_displays_email_field(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="email"')

    def test_creates_user_with_email(self):
        response = self.client.post(
            self.url,
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password1': 'Strongpass123',
                'password2': 'Strongpass123',
            }
        )
        self.assertRedirects(response, reverse('user_management'))
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
