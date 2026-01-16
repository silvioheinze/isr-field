from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from ..models import Typology, TypologyEntry


class TypologyVisibilityTests(TestCase):
    """Tests for typology visibility functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.superuser = User.objects.create_user(
            username='superuser',
            email='super@example.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123'
        )
        
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123'
        )
        
        # Create typologies with different visibility
        self.public_typology = Typology.objects.create(
            name='Public Typology',
            created_by=self.owner,
            is_public=True
        )
        
        self.private_typology = Typology.objects.create(
            name='Private Typology',
            created_by=self.owner,
            is_public=False
        )
    
    def test_can_access_superuser_sees_all(self):
        """Test that superusers can access all typologies"""
        self.assertTrue(self.public_typology.can_access(self.superuser))
        self.assertTrue(self.private_typology.can_access(self.superuser))
    
    def test_can_access_public_visible_to_all(self):
        """Test that public typologies are visible to all users"""
        self.assertTrue(self.public_typology.can_access(self.owner))
        self.assertTrue(self.public_typology.can_access(self.regular_user))
        self.assertTrue(self.public_typology.can_access(self.superuser))
    
    def test_can_access_private_only_to_owner(self):
        """Test that private typologies are only visible to owner"""
        self.assertTrue(self.private_typology.can_access(self.owner))
        self.assertFalse(self.private_typology.can_access(self.regular_user))
        self.assertTrue(self.private_typology.can_access(self.superuser))
    
    def test_typology_detail_view_respects_visibility(self):
        """Test that typology detail view respects visibility"""
        client = Client()
        
        # Owner can access their private typology
        client.force_login(self.owner)
        response = client.get(reverse('typology_detail', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 200)
        
        # Regular user cannot access private typology
        client.force_login(self.regular_user)
        response = client.get(reverse('typology_detail', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 403)
        
        # Regular user can access public typology
        response = client.get(reverse('typology_detail', args=[self.public_typology.id]))
        self.assertEqual(response.status_code, 200)
        
        # Superuser can access all
        client.force_login(self.superuser)
        response = client.get(reverse('typology_detail', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_typology_edit_view_respects_visibility(self):
        """Test that typology edit view respects visibility and allows superuser"""
        client = Client()
        
        # Owner can edit their typology
        client.force_login(self.owner)
        response = client.get(reverse('typology_edit', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 200)
        
        # Regular user cannot edit private typology
        client.force_login(self.regular_user)
        response = client.get(reverse('typology_edit', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 403)
        
        # Superuser can edit any typology
        client.force_login(self.superuser)
        response = client.get(reverse('typology_edit', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_typology_edit_can_change_visibility(self):
        """Test that typology edit can change visibility"""
        client = Client()
        client.force_login(self.owner)
        
        # Change from private to public
        response = client.post(
            reverse('typology_edit', args=[self.private_typology.id]),
            {
                'name': 'Private Typology',
                'is_public': 'on'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.private_typology.refresh_from_db()
        self.assertTrue(self.private_typology.is_public)
        
        # Change from public to private
        response = client.post(
            reverse('typology_edit', args=[self.public_typology.id]),
            {
                'name': 'Public Typology',
                # is_public not set
            }
        )
        self.assertEqual(response.status_code, 302)
        self.public_typology.refresh_from_db()
        self.assertFalse(self.public_typology.is_public)
    
    def test_typology_export_respects_visibility(self):
        """Test that typology export respects visibility"""
        client = Client()
        
        # Regular user cannot export private typology
        client.force_login(self.regular_user)
        response = client.get(reverse('typology_export', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 403)
        
        # Regular user can export public typology
        response = client.get(reverse('typology_export', args=[self.public_typology.id]))
        self.assertEqual(response.status_code, 200)
        
        # Owner can export their typology
        client.force_login(self.owner)
        response = client.get(reverse('typology_export', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 200)
        
        # Superuser can export any typology
        client.force_login(self.superuser)
        response = client.get(reverse('typology_export', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_typology_list_shows_visibility_badges(self):
        """Test that typology list shows visibility badges"""
        client = Client()
        client.force_login(self.owner)
        
        response = client.get(reverse('typology_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        
        # Check for visibility badges
        self.assertIn('Public', content)
        self.assertIn('Private', content)
    
    def test_typology_detail_shows_visibility(self):
        """Test that typology detail shows visibility status"""
        client = Client()
        client.force_login(self.owner)
        
        response = client.get(reverse('typology_detail', args=[self.public_typology.id]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Public', content)
        
        response = client.get(reverse('typology_detail', args=[self.private_typology.id]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Private', content)
