from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from ..models import Typology, TypologyEntry


class TypologyListPermissionsTestCase(TestCase):
    """Test that can_create_typologies is properly passed to typology list template"""
    
    def setUp(self):
        """Set up test data"""
        self.superuser = User.objects.create_user(
            username='superuser',
            email='super@example.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123'
        )
        
        self.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create typologies with different visibility
        self.public_typology = Typology.objects.create(
            name='Public Typology',
            created_by=self.regular_user,
            is_public=True
        )
        TypologyEntry.objects.create(
            typology=self.public_typology,
            code=1,
            category='A',
            name='Public Entry'
        )
        
        self.private_typology = Typology.objects.create(
            name='Private Typology',
            created_by=self.regular_user,
            is_public=False
        )
        TypologyEntry.objects.create(
            typology=self.private_typology,
            code=2,
            category='B',
            name='Private Entry'
        )
        
        self.other_user_typology = Typology.objects.create(
            name='Other User Typology',
            created_by=self.other_user,
            is_public=False
        )
        TypologyEntry.objects.create(
            typology=self.other_user_typology,
            code=3,
            category='C',
            name='Other Entry'
        )
    
    def test_superuser_sees_create_button(self):
        """Test that superuser sees the create typology button"""
        client = Client()
        client.force_login(self.superuser)
        
        response = client.get(reverse('typology_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that can_create_typologies is True in context
        self.assertIn('can_create_typologies', response.context)
        self.assertTrue(response.context['can_create_typologies'])
        
        # Check that the button appears in HTML
        content = response.content.decode()
        self.assertIn('Create New Typology', content)
        self.assertIn('/typologies/create/', content)
    
    def test_staff_user_sees_create_button(self):
        """Test that staff user sees the create typology button"""
        client = Client()
        client.force_login(self.staff_user)
        
        response = client.get(reverse('typology_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that can_create_typologies is True in context
        self.assertIn('can_create_typologies', response.context)
        self.assertTrue(response.context['can_create_typologies'])
        
        # Check that the button appears in HTML
        content = response.content.decode()
        self.assertIn('Create New Typology', content)
    
    def test_regular_user_no_create_button(self):
        """Test that regular user doesn't see the create typology button"""
        client = Client()
        client.force_login(self.regular_user)
        
        response = client.get(reverse('typology_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that can_create_typologies is False in context
        self.assertIn('can_create_typologies', response.context)
        self.assertFalse(response.context['can_create_typologies'])
        
        # Check that the button doesn't appear in HTML
        content = response.content.decode()
        self.assertNotIn('Create New Typology', content)

    def test_superuser_sees_all_typologies(self):
        """Test that superusers see all typologies regardless of visibility"""
        client = Client()
        client.force_login(self.superuser)
        
        response = client.get(reverse('typology_list'))
        self.assertEqual(response.status_code, 200)
        
        typologies = response.context['typologies']
        self.assertEqual(typologies.count(), 3)
        self.assertIn(self.public_typology, typologies)
        self.assertIn(self.private_typology, typologies)
        self.assertIn(self.other_user_typology, typologies)

    def test_regular_user_sees_public_and_own_typologies(self):
        """Test that regular users see public typologies and their own private ones"""
        client = Client()
        client.force_login(self.regular_user)
        
        response = client.get(reverse('typology_list'))
        self.assertEqual(response.status_code, 200)
        
        typologies = response.context['typologies']
        self.assertEqual(typologies.count(), 2)
        self.assertIn(self.public_typology, typologies)
        self.assertIn(self.private_typology, typologies)
        self.assertNotIn(self.other_user_typology, typologies)

    def test_user_cannot_see_other_users_private_typologies(self):
        """Test that users cannot see other users' private typologies"""
        client = Client()
        client.force_login(self.regular_user)
        
        response = client.get(reverse('typology_list'))
        self.assertEqual(response.status_code, 200)
        
        typologies = response.context['typologies']
        # Should only see public and own typologies
        self.assertNotIn(self.other_user_typology, typologies)

    def test_public_typology_visible_to_all_users(self):
        """Test that public typologies are visible to all users"""
        client = Client()
        client.force_login(self.other_user)
        
        response = client.get(reverse('typology_list'))
        self.assertEqual(response.status_code, 200)
        
        typologies = response.context['typologies']
        # Should see public typology and own typology
        self.assertIn(self.public_typology, typologies)
        self.assertIn(self.other_user_typology, typologies)
        self.assertNotIn(self.private_typology, typologies)
