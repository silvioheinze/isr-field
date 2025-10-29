from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from ..models import DataSet


class DatasetListPermissionsTestCase(TestCase):
    """Test that can_create_datasets is properly passed to dataset list template"""
    
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
        
        # Create test datasets
        self.owned_dataset = DataSet.objects.create(
            name='Owned Dataset',
            description='Dataset owned by regular user',
            owner=self.regular_user
        )
        
        self.other_dataset = DataSet.objects.create(
            name='Other Dataset',
            description='Dataset owned by other user',
            owner=self.other_user
        )
        
        self.public_dataset = DataSet.objects.create(
            name='Public Dataset',
            description='Public dataset',
            owner=self.other_user,
            is_public=True
        )
    
    def test_superuser_sees_create_button(self):
        """Test that superuser sees the create dataset button"""
        client = Client()
        client.force_login(self.superuser)
        
        response = client.get(reverse('dataset_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that can_create_datasets is True in context
        self.assertIn('can_create_datasets', response.context)
        self.assertTrue(response.context['can_create_datasets'])
        
        # Check that the button appears in HTML
        content = response.content.decode()
        self.assertIn('Create New Dataset', content)
        self.assertIn('/datasets/create/', content)
    
    def test_staff_user_sees_create_button(self):
        """Test that staff user sees the create dataset button"""
        client = Client()
        client.force_login(self.staff_user)
        
        response = client.get(reverse('dataset_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that can_create_datasets is True in context
        self.assertIn('can_create_datasets', response.context)
        self.assertTrue(response.context['can_create_datasets'])
        
        # Check that the button appears in HTML
        content = response.content.decode()
        self.assertIn('Create New Dataset', content)
    
    def test_regular_user_no_create_button(self):
        """Test that regular user doesn't see the create dataset button"""
        client = Client()
        client.force_login(self.regular_user)
        
        response = client.get(reverse('dataset_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that can_create_datasets is False in context
        self.assertIn('can_create_datasets', response.context)
        self.assertFalse(response.context['can_create_datasets'])
        
        # Check that the button doesn't appear in HTML
        content = response.content.decode()
        self.assertNotIn('Create New Dataset', content)
    
    def test_superuser_sees_all_datasets(self):
        """Test that superuser sees all datasets regardless of access permissions"""
        client = Client()
        client.force_login(self.superuser)
        
        response = client.get(reverse('dataset_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that all datasets are in the context
        datasets = response.context['datasets']
        dataset_names = [dataset.name for dataset in datasets]
        
        # Superuser should see all datasets
        self.assertIn('Owned Dataset', dataset_names)
        self.assertIn('Other Dataset', dataset_names)
        self.assertIn('Public Dataset', dataset_names)
        self.assertEqual(len(datasets), 3)
    
    def test_regular_user_sees_only_accessible_datasets(self):
        """Test that regular user sees only datasets they have access to"""
        client = Client()
        client.force_login(self.regular_user)
        
        response = client.get(reverse('dataset_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that only accessible datasets are in the context
        datasets = response.context['datasets']
        dataset_names = [dataset.name for dataset in datasets]
        
        # Regular user should see owned dataset and public dataset, but not other user's private dataset
        self.assertIn('Owned Dataset', dataset_names)
        self.assertIn('Public Dataset', dataset_names)
        self.assertNotIn('Other Dataset', dataset_names)
        self.assertEqual(len(datasets), 2)
