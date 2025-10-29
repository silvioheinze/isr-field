from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse


class UserManagementGroupsTestCase(TestCase):
    """Test that groups are displayed in user management"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test groups
        self.managers_group = Group.objects.create(name='Managers')
        self.editors_group = Group.objects.create(name='Editors')
    
    def test_user_management_shows_groups(self):
        """Test that user management view shows all groups"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 200)
        
        # Check that groups are in the context
        self.assertIn('groups', response.context)
        groups = response.context['groups']
        self.assertEqual(groups.count(), 2)
        
        # Check that both groups are present
        group_names = [group.name for group in groups]
        self.assertIn('Managers', group_names)
        self.assertIn('Editors', group_names)
    
    def test_modify_user_groups_shows_groups(self):
        """Test that modify user groups view shows all groups"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('modify_user_groups', kwargs={'user_id': self.user.id}))
        self.assertEqual(response.status_code, 200)
        
        # Check that groups are in the context
        self.assertIn('groups', response.context)
        groups = response.context['groups']
        self.assertEqual(groups.count(), 2)
        
        # Check that both groups are present
        group_names = [group.name for group in groups]
        self.assertIn('Managers', group_names)
        self.assertIn('Editors', group_names)
