from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse


class DebugGroupsTestCase(TestCase):
    """Debug test to check groups in user management"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create the Managers group
        self.managers_group = Group.objects.create(name='Managers')
    
    def test_debug_user_management_response(self):
        """Debug the user management response"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        print(f"\n=== User Management Response Debug ===")
        print(f"Response status: {response.status_code}")
        print(f"Groups in context: {response.context.get('groups', 'NOT FOUND')}")
        
        if 'groups' in response.context:
            groups = response.context['groups']
            print(f"Number of groups: {groups.count()}")
            for group in groups:
                print(f"  - {group.name} (ID: {group.id})")
        
        # Check if "Managers" appears in the HTML
        if 'Managers' in content:
            print("✅ 'Managers' found in HTML response")
        else:
            print("❌ 'Managers' NOT found in HTML response")
            print("HTML content snippet:")
            print(content[content.find('Groups'):content.find('Groups') + 500])
        
        # Check if groups table exists
        if 'Group Name' in content:
            print("✅ Groups table found in HTML")
        else:
            print("❌ Groups table NOT found in HTML")
