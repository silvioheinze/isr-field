from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse


class CreateGroupViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin)
        self.url = reverse('create_group')

    def test_form_displays_group_name_field(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="name"')

    def test_creates_group(self):
        response = self.client.post(self.url, {'name': 'Field Editors'})
        self.assertRedirects(response, reverse('user_management'))
        self.assertTrue(Group.objects.filter(name='Field Editors').exists())
