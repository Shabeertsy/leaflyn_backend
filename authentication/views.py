from django.contrib.auth import authenticate, get_user_model
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,IsAuthenticated
from django.conf import settings
from datetime import datetime, timedelta
from rest_framework_simplejwt.tokens import RefreshToken
import re

from .serializers import (
    ProfileRegistrationSerializer, 
    SendOTPSerializer, 
    VerifyOTPSerializer,
    ProfileSerializer
)
from .otp_utils import create_otp, send_otp_email, send_otp_sms, verify_otp, resend_otp


from google.oauth2 import id_token
from google.auth.transport import requests


User = get_user_model()


class RegisterAPIView(generics.CreateAPIView):
    """Traditional registration with email/phone and password"""
    serializer_class = ProfileRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        full_name = data.pop('full_name', '').strip()
        if full_name:
            name_parts = full_name.split(' ', 1)
            data['first_name'] = name_parts[0]
            data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "User registered successfully."},
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    """Traditional login with email/phone and password"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        identifier = request.data.get('email') or request.data.get('phone_number')
        password = request.data.get('password')
        
        if not identifier or not password:
            return Response(
                {'error': 'Email/Phone and password are required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Try to find user by email or phone
        user = None
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(email_pattern, identifier):
            user = authenticate(username=identifier, password=password)
        else:
            # Try to find user by phone number
            try:
                user_obj = User.objects.get(phone_number=identifier)
                if user_obj.check_password(password):
                    user = user_obj
            except User.DoesNotExist:
                pass
        
        if user is None:
            return Response(
                {'error': 'Invalid credentials.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': ProfileSerializer(user).data
        }, status=status.HTTP_200_OK)


class SendOTPView(APIView):
    """Send OTP to email or phone number"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contact = serializer.validated_data['contact']
        contact_type = serializer.validated_data['contact_type']
        
        # Create OTP
        otp = create_otp(contact, contact_type)
        
        # Send OTP based on contact type
        if contact_type == 'email':
            success = send_otp_email(contact, otp.otp_code)
            message = "OTP sent to your email"
        else:  # phone
            success = send_otp_sms(contact, otp.otp_code)
            message = "OTP sent to your phone"
        
        if not success:
            return Response(
                {'error': f'Failed to send OTP via {contact_type}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': message,
            'contact': contact,
            'contact_type': contact_type,
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """Verify OTP and login/register user"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contact = serializer.validated_data['contact']
        otp_code = serializer.validated_data['otp_code']
        
        # Verify OTP
        success, message, otp = verify_otp(contact, otp_code)
        
        if not success:
            return Response(
                {'error': message}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine contact type
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_email = re.match(email_pattern, contact)
        
        # Find or create user
        user = None
        created = False
        
        if is_email:
            user, created = User.objects.get_or_create(
                email=contact,
                defaults={
                    'is_verified': True,
                    'first_name': serializer.validated_data.get('first_name', ''),
                    'last_name': serializer.validated_data.get('last_name', ''),
                }
            )
        else:
            user, created = User.objects.get_or_create(
                phone_number=contact,
                defaults={
                    'is_verified': True,
                    'first_name': serializer.validated_data.get('first_name', ''),
                    'last_name': serializer.validated_data.get('last_name', ''),
                }
            )
        
        # Update verification status if user already existed
        if not created and not user.is_verified:
            user.is_verified = True
            user.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful' if not created else 'Account created and logged in',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': ProfileSerializer(user).data,
            'is_new_user': created
        }, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    """Resend OTP to email or phone number"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contact = serializer.validated_data['contact']
        contact_type = serializer.validated_data['contact_type']
        
        # Resend OTP
        success, message = resend_otp(contact, contact_type)
        
        if not success:
            return Response(
                {'error': message}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': message,
            'contact': contact
        }, status=status.HTTP_200_OK)


class PersonalInfo(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    
    def get_object(self):
        return self.request.user



class RegisterUserAndAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        user = request.user

        # Update password if provided
        password = data.get('password')
        if password:
            user.set_password(password)
            user.save()
        
        # Update contact info if provided (email or phone)
        email = data.get("email")
        phone_number = data.get("phone_number")
        updated_fields = []

        if email and user.email != email:
            user.email = email
            updated_fields.append("email")
        if phone_number and getattr(user, "phone_number", None) != phone_number:
            user.phone_number = phone_number
            updated_fields.append("phone_number")
        
        # Optional: update name
        full_name = data.get('full_name', '').strip()
        if full_name:
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            if user.first_name != first_name:
                user.first_name = first_name
                updated_fields.append("first_name")
            if user.last_name != last_name:
                user.last_name = last_name
                updated_fields.append("last_name")
        
        if updated_fields:
            user.save(update_fields=updated_fields)

        # Required address fields
        address_fields = [
            'building_name_number',  
            'place_street',         
            'city',                 
            'district',             
            'state',                
            'pin_code',             
        ]
        address_data = {field: data.get(field) for field in address_fields}

        # Validate minimum required address fields
        required_address_fields = ['place_street', 'city', 'state', 'pin_code']
        missing_address = [field for field in required_address_fields if not data.get(field)]
        if missing_address:
            return Response({'error': f"Missing required address fields: {', '.join(missing_address)}"}, status=status.HTTP_400_BAD_REQUEST)

        from user.models import ShippingAddress

        shipping_address = ShippingAddress.objects.create(
            user=user,
            address_line_1=address_data.get('place_street'),
            address_line_2=address_data.get('building_name_number', ''),
            city=address_data.get('city'),
            district=address_data.get('district', ''),
            state=address_data.get('state'),
            pin_code=address_data.get('pin_code'),
        )

        # Serialize user and address (token comes from request header, do not re-issue)
        user_data = ProfileSerializer(user).data
        address_serializer_cls = None
        try:
            from user.serializers import AddressSerializer
            address_serializer_cls = AddressSerializer
        except ImportError:
            address_serializer_cls = None

        address_data_response = (
            address_serializer_cls(shipping_address).data if address_serializer_cls else None
        )

        return Response(
            {
                "message": "User address updated/added successfully.",
                "user": user_data,
                "address": address_data_response,
            },
            status=status.HTTP_200_OK,
        )




class GoogleAuthView(APIView):
    def post(self, request):
        token = request.data.get("auth_token")

        try:
            google_user = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            email = google_user["email"]
            name = google_user.get("name", "")
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"email": email, "first_name": name}
            )

            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                 'user': ProfileSerializer(user).data,
                "email": user.email,
                "name": user.first_name,
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
