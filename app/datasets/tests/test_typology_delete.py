from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from ..models import Typology, TypologyEntry


class TypologyDeleteViewTests(TestCase):
    """Tests for deleting typologies."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        self.superuser = User.objects.create_user(
            username='superuser',
            email='super@example.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        self.typology = Typology.objects.create(name='Delete Me', created_by=self.owner)
        TypologyEntry.objects.create(typology=self.typology, code=1, category='A', name='Alpha')
        self.delete_url = reverse('typology_delete', args=[self.typology.id])

    def test_owner_can_delete_typology(self):
        client = Client()
        client.force_login(self.owner)

        response = client.post(self.delete_url)
        self.assertRedirects(response, reverse('typology_list'))
        self.assertFalse(Typology.objects.filter(id=self.typology.id).exists())
        self.assertEqual(TypologyEntry.objects.filter(typology=self.typology).count(), 0)

    def test_get_renders_confirmation_for_owner(self):
        client = Client()
        client.force_login(self.owner)

        response = client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Typology')
        self.assertContains(response, 'This action cannot be undone')
        self.assertIn('<form method="post"', response.content.decode('utf-8'))

    def test_non_owner_cannot_delete(self):
        client = Client()
        client.force_login(self.other_user)

        response = client.get(self.delete_url)
        self.assertEqual(response.status_code, 403)

        response = client.post(self.delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Typology.objects.filter(id=self.typology.id).exists())

    def test_redirects_to_list_after_delete_even_with_next(self):
        client = Client()
        client.force_login(self.owner)

        response = client.post(f"{self.delete_url}?next=/typologies/", follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse('typology_list'))
        self.assertFalse(Typology.objects.filter(id=self.typology.id).exists())

    def test_superuser_can_delete_typology(self):
        """Test that superusers can delete any typology"""
        client = Client()
        client.force_login(self.superuser)

        response = client.post(self.delete_url)
        self.assertRedirects(response, reverse('typology_list'))
        self.assertFalse(Typology.objects.filter(id=self.typology.id).exists())
