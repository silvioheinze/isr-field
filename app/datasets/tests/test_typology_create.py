from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from ..models import Typology, TypologyEntry


class TypologyCreateViewTests(TestCase):
    """Tests for creating typologies with entry data."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='creator',
            email='creator@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.create_url = reverse('typology_create')

    def test_create_typology_with_entries(self):
        response = self.client.post(
            self.create_url,
            {
                'name': 'Land Use Codes',
                'entry_code_1': '1',
                'entry_category_1': 'Residential',
                'entry_name_1': 'Apartment',
                'entry_code_2': '2',
                'entry_category_2': 'Commercial',
                'entry_name_2': 'Retail',
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Typology.objects.filter(name='Land Use Codes').exists())
        typology = Typology.objects.get(name='Land Use Codes')
        entries = typology.entries.order_by('code')
        self.assertEqual(entries.count(), 2)
        self.assertEqual(entries[0].code, 1)
        self.assertEqual(entries[0].category, 'Residential')
        self.assertEqual(entries[0].name, 'Apartment')
        self.assertEqual(entries[1].code, 2)

    def test_create_typology_requires_entries(self):
        response = self.client.post(
            self.create_url,
            {
                'name': 'Empty Typology',
                # No entry fields submitted
            },
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Typology.objects.filter(name='Empty Typology').exists())
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Please add at least one typology entry' in str(message) for message in messages))
