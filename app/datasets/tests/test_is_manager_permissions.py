from django.test import TestCase
from django.contrib.auth.models import User, Group
from ..views.auth_views import is_manager


class IsManagerPermissionsTestCase(TestCase):
    """Test the is_manager function with different user types"""
    
    def setUp(self):
        """Set up test data"""
        # Create Managers group
        self.managers_group = Group.objects.create(name='Managers')
        
        # Create different types of users
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
        
        self.manager_user = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123'
        )
        self.manager_user.groups.add(self.managers_group)
        
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123'
        )
    
    def test_superuser_can_create_datasets(self):
        """Test that superusers can create datasets"""
        self.assertTrue(is_manager(self.superuser))
        self.assertTrue(self.superuser.is_superuser)
        self.assertTrue(self.superuser.is_staff)
    
    def test_staff_user_can_create_datasets(self):
        """Test that staff users can create datasets"""
        self.assertTrue(is_manager(self.staff_user))
        self.assertTrue(self.staff_user.is_staff)
        self.assertFalse(self.staff_user.is_superuser)
    
    def test_manager_group_user_can_create_datasets(self):
        """Test that users in Managers group can create datasets"""
        self.assertTrue(is_manager(self.manager_user))
        self.assertTrue(self.manager_user.groups.filter(name='Managers').exists())
        self.assertFalse(self.manager_user.is_staff)
        self.assertFalse(self.manager_user.is_superuser)
    
    def test_regular_user_cannot_create_datasets(self):
        """Test that regular users cannot create datasets"""
        self.assertFalse(is_manager(self.regular_user))
        self.assertFalse(self.regular_user.is_staff)
        self.assertFalse(self.regular_user.is_superuser)
        self.assertFalse(self.regular_user.groups.filter(name='Managers').exists())
    
    def test_user_with_multiple_qualifications(self):
        """Test user who is both staff and in Managers group"""
        staff_manager = User.objects.create_user(
            username='staff_manager',
            email='staff_manager@example.com',
            password='testpass123',
            is_staff=True
        )
        staff_manager.groups.add(self.managers_group)
        
        # Should still return True (any qualification is enough)
        self.assertTrue(is_manager(staff_manager))
        self.assertTrue(staff_manager.is_staff)
        self.assertTrue(staff_manager.groups.filter(name='Managers').exists())
