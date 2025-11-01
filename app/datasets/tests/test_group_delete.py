from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse


class DeleteGroupViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.member = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='testpass123'
        )
        self.group = Group.objects.create(name='Field Workers')
        self.group.user_set.add(self.member)
        self.client = Client()
        self.client.force_login(self.admin)
        self.url = reverse('delete_group', args=[self.group.id])

    def test_get_renders_confirmation(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Group')
        self.assertContains(response, self.group.name)

    def test_owner_can_delete_group(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('user_management'))
        self.assertFalse(Group.objects.filter(id=self.group.id).exists())

    def test_requires_permission(self):
        user = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123'
        )
        client = Client()
        client.force_login(user)

        response = client.get(self.url)
        self.assertEqual(response.status_code, 403)
        response = client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Group.objects.filter(id=self.group.id).exists())
