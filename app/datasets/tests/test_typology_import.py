from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Typology, TypologyEntry


class TypologyImportViewTests(TestCase):
    """Tests for the typology CSV import workflow."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123'
        )
        self.typology = Typology.objects.create(
            name='Land Use',
            created_by=self.user
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.import_url = reverse('typology_import', args=[self.typology.id])
        self.detail_url = reverse('typology_detail', args=[self.typology.id])

    def _post_csv(self, content: str, follow=False):
        csv_file = SimpleUploadedFile(
            'typology.csv',
            content.encode('utf-8'),
            content_type='text/csv'
        )
        return self.client.post(self.import_url, {'csv_file': csv_file}, follow=follow)

    def test_successful_import_creates_entries(self):
        response = self._post_csv(
            "code,category,name\n1,Residential,Apartment\n2,Commercial,Shop"
        )
        self.assertRedirects(response, self.detail_url)
        self.assertEqual(TypologyEntry.objects.filter(typology=self.typology).count(), 2)

    def test_import_reports_missing_required_columns(self):
        response = self._post_csv(
            "code,category\n1,Residential"
        )
        self.assertRedirects(response, self.import_url)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Missing required columns' in str(message) for message in messages))
        self.assertEqual(TypologyEntry.objects.filter(typology=self.typology).count(), 0)

    def test_import_handles_blank_header_without_crashing(self):
        response = self._post_csv(
            "code,category,\n1,Industrial,Factory"
        )
        self.assertRedirects(response, self.import_url)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Missing required columns' in str(message) for message in messages))
        self.assertEqual(TypologyEntry.objects.filter(typology=self.typology).count(), 0)
