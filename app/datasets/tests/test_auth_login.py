from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class EmailLoginViewTests(TestCase):
    def setUp(self):
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password=self.password,
        )

    def test_login_with_email_success(self):
        response = self.client.post(
            reverse('login'),
            {'username': self.user.email, 'password': self.password},
        )
        self.assertRedirects(
            response,
            reverse('dashboard'),
            fetch_redirect_response=False,
        )

        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)

    def test_login_with_incorrect_email(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'unknown@example.com', 'password': self.password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password.', status_code=200)

    def test_login_with_wrong_password(self):
        response = self.client.post(
            reverse('login'),
            {'username': self.user.email, 'password': 'wrong-pass'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password.', status_code=200)

