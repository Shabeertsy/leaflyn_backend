from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import OTP
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class OTPAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.send_otp_url = reverse('send-otp')
        self.verify_otp_url = reverse('verify-otp')
        self.resend_otp_url = reverse('resend-otp')
        self.email = "test@example.com"
        self.phone = "+1234567890"

    def test_send_otp_email(self):
        """Test sending OTP to email"""
        data = {"contact": self.email}
        response = self.client.post(self.send_otp_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTP.objects.filter(contact=self.email).exists())
        self.assertEqual(response.data['contact_type'], 'email')

    def test_send_otp_phone(self):
        """Test sending OTP to phone"""
        data = {"contact": self.phone}
        response = self.client.post(self.send_otp_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTP.objects.filter(contact=self.phone).exists())
        self.assertEqual(response.data['contact_type'], 'phone')

    def test_verify_otp_create_user(self):
        """Test verifying OTP creates a new user"""
        # First send OTP
        self.client.post(self.send_otp_url, {"contact": self.email})
        otp_obj = OTP.objects.get(contact=self.email)
        
        # Verify OTP
        data = {
            "contact": self.email,
            "otp_code": otp_obj.otp_code,
            "first_name": "Test",
            "last_name": "User"
        }
        response = self.client.post(self.verify_otp_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(email=self.email).exists())
        user = User.objects.get(email=self.email)
        self.assertTrue(user.is_verified)
        self.assertIn('access', response.data)
        self.assertTrue(response.data['is_new_user'])

    def test_verify_otp_existing_user(self):
        """Test verifying OTP for existing user logs them in"""
        # Create user first
        user = User.objects.create_user(email=self.email, password="password123")
        
        # Send OTP
        self.client.post(self.send_otp_url, {"contact": self.email})
        otp_obj = OTP.objects.get(contact=self.email)
        
        # Verify OTP
        data = {
            "contact": self.email,
            "otp_code": otp_obj.otp_code
        }
        response = self.client.post(self.verify_otp_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_new_user'])
        self.assertIn('access', response.data)

    def test_invalid_otp(self):
        """Test verifying with invalid OTP code"""
        self.client.post(self.send_otp_url, {"contact": self.email})
        
        data = {
            "contact": self.email,
            "otp_code": "000000"  # Wrong code
        }
        response = self.client.post(self.verify_otp_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_otp(self):
        """Test verifying expired OTP"""
        self.client.post(self.send_otp_url, {"contact": self.email})
        otp_obj = OTP.objects.get(contact=self.email)
        
        # Manually expire the OTP
        otp_obj.expires_at = timezone.now() - timedelta(minutes=1)
        otp_obj.save()
        
        data = {
            "contact": self.email,
            "otp_code": otp_obj.otp_code
        }
        response = self.client.post(self.verify_otp_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expired', response.data['error'].lower())

    def test_resend_otp(self):
        """Test resending OTP generates a new code"""
        # Send first OTP
        self.client.post(self.send_otp_url, {"contact": self.email})
        otp1 = OTP.objects.get(contact=self.email)
        
        # Resend OTP
        response = self.client.post(self.resend_otp_url, {"contact": self.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that a new OTP was created
        otp2 = OTP.objects.filter(contact=self.email).latest('created_at')
        self.assertNotEqual(otp1.otp_code, otp2.otp_code)
        
        # Check that old OTP is inactive
        otp1.refresh_from_db()
        self.assertFalse(otp1.active_status)
