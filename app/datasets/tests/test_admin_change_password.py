from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.auth import authenticate


class AdminChangePasswordViewTests(TestCase):
    """Tests for admin_change_user_password_view (superuser-only password change)"""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        self.target_user = User.objects.create_user(
            username='targetuser',
            email='target@example.com',
            password='oldpass123'
        )
        self.client = Client()

    def test_superuser_can_access_change_password_page(self):
        """Superuser can access the change password page for any user"""
        self.client.force_login(self.superuser)
        url = reverse('admin_change_user_password', args=[self.target_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change Password')
        self.assertContains(response, self.target_user.username)
        self.assertContains(response, 'new_password1')
        self.assertContains(response, 'new_password2')

    def test_superuser_can_change_user_password(self):
        """Superuser can successfully change another user's password"""
        self.client.force_login(self.superuser)
        url = reverse('admin_change_user_password', args=[self.target_user.id])
        new_password = 'NewSecurePass123!'
        response = self.client.post(url, {
            'new_password1': new_password,
            'new_password2': new_password,
        })
        self.assertRedirects(response, reverse('user_management'))

        # Verify the new password works
        updated_user = authenticate(username=self.target_user.username, password=new_password)
        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.id, self.target_user.id)

        # Verify old password no longer works
        old_auth = authenticate(username=self.target_user.username, password='oldpass123')
        self.assertIsNone(old_auth)

    def test_staff_user_cannot_access_change_password_page(self):
        """Staff user (non-superuser) cannot access the change password page"""
        self.client.force_login(self.staff_user)
        url = reverse('admin_change_user_password', args=[self.target_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_regular_user_cannot_access_change_password_page(self):
        """Regular user cannot access the change password page"""
        self.client.force_login(self.regular_user)
        url = reverse('admin_change_user_password', args=[self.target_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated user is redirected to login"""
        url = reverse('admin_change_user_password', args=[self.target_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)

    def test_nonexistent_user_returns_404(self):
        """Changing password for nonexistent user returns 404"""
        self.client.force_login(self.superuser)
        url = reverse('admin_change_user_password', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_password_mismatch_shows_form_errors(self):
        """Password mismatch shows form errors and does not change password"""
        self.client.force_login(self.superuser)
        url = reverse('admin_change_user_password', args=[self.target_user.id])
        response = self.client.post(url, {
            'new_password1': 'NewPass123!',
            'new_password2': 'DifferentPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change Password')
        # Form should have validation errors (password mismatch)
        self.assertTrue(response.context['form'].errors)

        # Old password should still work
        auth = authenticate(username=self.target_user.username, password='oldpass123')
        self.assertIsNotNone(auth)

    def test_empty_password_shows_form_errors(self):
        """Empty password shows form errors"""
        self.client.force_login(self.superuser)
        url = reverse('admin_change_user_password', args=[self.target_user.id])
        response = self.client.post(url, {
            'new_password1': '',
            'new_password2': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change Password')

    def test_superuser_can_change_own_password(self):
        """Superuser can change their own password"""
        self.client.force_login(self.superuser)
        url = reverse('admin_change_user_password', args=[self.superuser.id])
        new_password = 'NewAdminPass456!'
        response = self.client.post(url, {
            'new_password1': new_password,
            'new_password2': new_password,
        })
        # Redirect to user_management (session may be invalidated when changing own password)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('user_management'))

        # Verify new password works
        updated = User.objects.get(id=self.superuser.id)
        self.assertTrue(updated.check_password(new_password))
