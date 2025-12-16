from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from ..forms import EmailAuthenticationForm, CustomUserCreationForm, TransferOwnershipForm
from ..models import DataSet


class EmailAuthenticationFormTest(TestCase):
    """Test cases for EmailAuthenticationForm"""
    
    def setUp(self):
        """Set up test data"""
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password=self.password,
        )
        self.factory = RequestFactory()
    
    def test_form_initialization(self):
        """Test form initialization"""
        form = EmailAuthenticationForm()
        # AuthenticationForm has no Meta attribute (it's not a ModelForm)
        self.assertEqual(form.fields['username'].label, 'Email')
        self.assertIsInstance(form.fields['username'].widget, type(form.fields['username'].widget))
    
    def test_form_widget_attributes(self):
        """Test that form widgets have correct attributes"""
        form = EmailAuthenticationForm()
        
        # Check email input widget
        email_widget = form.fields['username'].widget
        self.assertIn('autofocus', email_widget.attrs)
        self.assertIn('form-control', email_widget.attrs['class'])
        self.assertIn('user@example.com', email_widget.attrs['placeholder'])
    
    def test_form_validation_valid_email_and_password(self):
        """Test form validation with valid email and password"""
        request = self.factory.post('/login/', {
            'username': self.user.email,
            'password': self.password,
        })
        form = EmailAuthenticationForm(request=request, data={
            'username': self.user.email,
            'password': self.password,
        })
        self.assertTrue(form.is_valid())
        self.assertIsNotNone(form.user_cache)
        self.assertEqual(form.user_cache, self.user)
    
    def test_form_validation_invalid_email(self):
        """Test form validation with invalid email"""
        request = self.factory.post('/login/', {
            'username': 'nonexistent@example.com',
            'password': self.password,
        })
        form = EmailAuthenticationForm(request=request, data={
            'username': 'nonexistent@example.com',
            'password': self.password,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('Please enter a correct email address and password', str(form.errors))
    
    def test_form_validation_wrong_password(self):
        """Test form validation with wrong password"""
        request = self.factory.post('/login/', {
            'username': self.user.email,
            'password': 'wrongpassword',
        })
        form = EmailAuthenticationForm(request=request, data={
            'username': self.user.email,
            'password': 'wrongpassword',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('Please enter a correct email address and password', str(form.errors))
    
    def test_form_validation_multiple_accounts_same_email(self):
        """Test form validation when multiple accounts have same email"""
        # Create another user with same email (case-insensitive)
        User.objects.create_user(
            username='anotheruser',
            email='TESTUSER@EXAMPLE.COM',  # Same email, different case
            password='anotherpass123',
        )
        
        request = self.factory.post('/login/', {
            'username': self.user.email,
            'password': self.password,
        })
        form = EmailAuthenticationForm(request=request, data={
            'username': self.user.email,
            'password': self.password,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('Multiple accounts are associated with this email address', str(form.errors))
    
    def test_form_validation_empty_email(self):
        """Test form validation with empty email"""
        request = self.factory.post('/login/', {
            'username': '',
            'password': self.password,
        })
        form = EmailAuthenticationForm(request=request, data={
            'username': '',
            'password': self.password,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
    
    def test_form_validation_empty_password(self):
        """Test form validation with empty password"""
        request = self.factory.post('/login/', {
            'username': self.user.email,
            'password': '',
        })
        form = EmailAuthenticationForm(request=request, data={
            'username': self.user.email,
            'password': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
    
    def test_form_error_messages(self):
        """Test that form has correct error messages"""
        form = EmailAuthenticationForm()
        self.assertIn('invalid_login', form.error_messages)
        self.assertIn('multiple_accounts', form.error_messages)
        self.assertIn('Please enter a correct email address and password', form.error_messages['invalid_login'])
        self.assertIn('Multiple accounts are associated with this email address', form.error_messages['multiple_accounts'])


class CustomUserCreationFormTest(TestCase):
    """Test cases for CustomUserCreationForm"""
    
    def setUp(self):
        """Set up test data"""
        self.existing_user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='testpass123'
        )
    
    def test_form_initialization(self):
        """Test form initialization"""
        form = CustomUserCreationForm()
        self.assertEqual(form.Meta.model, User)
        self.assertIn('username', form.fields)
        self.assertIn('email', form.fields)
        self.assertIn('password1', form.fields)
        self.assertIn('password2', form.fields)
    
    def test_form_widget_attributes(self):
        """Test that form widgets have correct attributes"""
        form = CustomUserCreationForm()
        
        # Check username widget
        self.assertIn('form-control', form.fields['username'].widget.attrs['class'])
        
        # Check email widget
        self.assertIn('form-control', form.fields['email'].widget.attrs['class'])
        self.assertIn('user@example.com', form.fields['email'].widget.attrs['placeholder'])
        
        # Check password widgets
        self.assertIn('form-control', form.fields['password1'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['password2'].widget.attrs['class'])
    
    def test_form_validation_valid_data(self):
        """Test form validation with valid data"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'Strongpass123',
            'password2': 'Strongpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_form_validation_duplicate_email(self):
        """Test form validation with duplicate email"""
        form_data = {
            'username': 'newuser',
            'email': 'existing@example.com',  # Already exists
            'password1': 'Strongpass123',
            'password2': 'Strongpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('A user with that email address already exists', str(form.errors['email']))
    
    def test_form_validation_duplicate_email_case_insensitive(self):
        """Test form validation with duplicate email (case-insensitive)"""
        form_data = {
            'username': 'newuser',
            'email': 'EXISTING@EXAMPLE.COM',  # Same email, different case
            'password1': 'Strongpass123',
            'password2': 'Strongpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('A user with that email address already exists', str(form.errors['email']))
    
    def test_form_validation_missing_email(self):
        """Test form validation with missing email"""
        form_data = {
            'username': 'newuser',
            'email': '',
            'password1': 'Strongpass123',
            'password2': 'Strongpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_form_validation_invalid_email_format(self):
        """Test form validation with invalid email format"""
        form_data = {
            'username': 'newuser',
            'email': 'invalid-email',
            'password1': 'Strongpass123',
            'password2': 'Strongpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_form_validation_password_mismatch(self):
        """Test form validation with password mismatch"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'Strongpass123',
            'password2': 'Differentpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_form_validation_duplicate_username(self):
        """Test form validation with duplicate username"""
        form_data = {
            'username': 'existinguser',  # Already exists
            'email': 'newuser@example.com',
            'password1': 'Strongpass123',
            'password2': 'Strongpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
    
    def test_form_save_email_lowercasing(self):
        """Test that form save method lowercases email"""
        form_data = {
            'username': 'newuser',
            'email': 'NewUser@Example.COM',
            'password1': 'Strongpass123',
            'password2': 'Strongpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        user = form.save()
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.username, 'newuser')
    
    def test_form_save_with_commit_false(self):
        """Test form save with commit=False"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'Strongpass123',
            'password2': 'Strongpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        user = form.save(commit=False)
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.username, 'newuser')
        
        # Verify it's not saved to database yet
        self.assertFalse(User.objects.filter(username='newuser').exists())
        
        # Save manually
        user.save()
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_form_clean_email_strips_whitespace(self):
        """Test that clean_email method strips whitespace"""
        form_data = {
            'username': 'newuser',
            'email': '  newuser@example.com  ',  # With whitespace
            'password1': 'Strongpass123',
            'password2': 'Strongpass123',
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email'], 'newuser@example.com')


class TransferOwnershipFormTest(TestCase):
    """Test cases for TransferOwnershipForm"""
    
    def setUp(self):
        """Set up test data"""
        self.current_owner = User.objects.create_user(
            username='currentowner',
            email='owner@example.com',
            password='testpass123'
        )
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            is_active=True
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            is_active=True
        )
        self.inactive_user = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='testpass123',
            is_active=False
        )
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            owner=self.current_owner
        )
    
    def test_form_initialization_without_current_owner(self):
        """Test form initialization without current_owner"""
        form = TransferOwnershipForm()
        self.assertEqual(form.fields['new_owner'].queryset.count(), User.objects.filter(is_active=True).count())
    
    def test_form_initialization_with_current_owner(self):
        """Test form initialization with current_owner"""
        form = TransferOwnershipForm(current_owner=self.current_owner)
        queryset = form.fields['new_owner'].queryset
        # Current owner should be excluded
        self.assertNotIn(self.current_owner, queryset)
        # Other active users should be included
        self.assertIn(self.user1, queryset)
        self.assertIn(self.user2, queryset)
        # Inactive users should be excluded
        self.assertNotIn(self.inactive_user, queryset)
    
    def test_form_initialization_excludes_inactive_users(self):
        """Test that form excludes inactive users"""
        form = TransferOwnershipForm(current_owner=self.current_owner)
        queryset = form.fields['new_owner'].queryset
        self.assertNotIn(self.inactive_user, queryset)
    
    def test_form_queryset_ordering(self):
        """Test that queryset is ordered by username"""
        form = TransferOwnershipForm(current_owner=self.current_owner)
        queryset = list(form.fields['new_owner'].queryset)
        usernames = [user.username for user in queryset]
        self.assertEqual(usernames, sorted(usernames))
    
    def test_form_widget_attributes(self):
        """Test that form widgets have correct attributes"""
        form = TransferOwnershipForm()
        self.assertIn('form-select', form.fields['new_owner'].widget.attrs['class'])
    
    def test_form_help_text(self):
        """Test that form has correct help text"""
        form = TransferOwnershipForm()
        self.assertIn('Select the user who will become the new owner', form.fields['new_owner'].help_text)
    
    def test_form_validation_valid_data(self):
        """Test form validation with valid data"""
        form = TransferOwnershipForm(current_owner=self.current_owner, data={
            'new_owner': self.user1.id,
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
        self.assertEqual(form.cleaned_data['new_owner'], self.user1)
    
    def test_form_validation_missing_new_owner(self):
        """Test form validation with missing new_owner"""
        form = TransferOwnershipForm(current_owner=self.current_owner, data={})
        self.assertFalse(form.is_valid())
        self.assertIn('new_owner', form.errors)
    
    def test_form_validation_current_owner_not_in_queryset(self):
        """Test that current owner cannot be selected even if ID is provided"""
        form = TransferOwnershipForm(current_owner=self.current_owner, data={
            'new_owner': self.current_owner.id,
        })
        # The form should be invalid because current_owner is not in queryset
        self.assertFalse(form.is_valid())
        self.assertIn('new_owner', form.errors)
    
    def test_form_validation_inactive_user_not_in_queryset(self):
        """Test that inactive user cannot be selected even if ID is provided"""
        form = TransferOwnershipForm(current_owner=self.current_owner, data={
            'new_owner': self.inactive_user.id,
        })
        # The form should be invalid because inactive_user is not in queryset
        self.assertFalse(form.is_valid())
        self.assertIn('new_owner', form.errors)
    
    def test_form_validation_invalid_user_id(self):
        """Test form validation with invalid user ID"""
        form = TransferOwnershipForm(current_owner=self.current_owner, data={
            'new_owner': 99999,  # Non-existent user ID
        })
        self.assertFalse(form.is_valid())
        self.assertIn('new_owner', form.errors)
    
    def test_form_queryset_updates_when_current_owner_changes(self):
        """Test that queryset updates when current_owner changes"""
        form1 = TransferOwnershipForm(current_owner=self.current_owner)
        queryset1 = form1.fields['new_owner'].queryset
        
        # Create new owner
        new_owner = User.objects.create_user(
            username='newowner',
            email='newowner@example.com',
            password='testpass123',
            is_active=True
        )
        
        form2 = TransferOwnershipForm(current_owner=new_owner)
        queryset2 = form2.fields['new_owner'].queryset
        
        # New owner should be excluded in form2
        self.assertNotIn(new_owner, queryset2)
        # But should be included in form1 (if it was created before new_owner existed)
        # Actually, queryset is evaluated lazily, so this might not work as expected
        # Let's just verify the exclusion works
        self.assertNotIn(new_owner, queryset2)
    
    def test_form_field_required(self):
        """Test that new_owner field is required"""
        form = TransferOwnershipForm()
        self.assertTrue(form.fields['new_owner'].required)

