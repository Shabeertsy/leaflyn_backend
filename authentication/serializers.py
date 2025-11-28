from rest_framework import serializers
from django.contrib.auth import get_user_model
import re

User = get_user_model()


class ProfileRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'phone_number', 'first_name', 'last_name', 'password', 'bio', 'user_type']

    def validate(self, data):
        email = data.get('email')
        phone_number = data.get('phone_number')
        
        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required")
        
        return data

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create_user(password=password, **validated_data)
        return user


class SendOTPSerializer(serializers.Serializer):
    """Serializer for sending OTP to email or phone"""
    contact = serializers.CharField(required=True)
    contact_type = serializers.ChoiceField(choices=['email', 'phone'], required=False)
    
    def validate_contact(self, value):
        """Validate and determine contact type"""
        # Check if it's an email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        # Check if it's a phone number (simple validation)
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        
        if re.match(email_pattern, value):
            return value
        elif re.match(phone_pattern, value.replace(' ', '').replace('-', '')):
            return value.replace(' ', '').replace('-', '')
        else:
            raise serializers.ValidationError("Invalid email or phone number format")
    
    def validate(self, data):
        contact = data.get('contact')
        contact_type = data.get('contact_type')
        
        # Auto-detect contact type if not provided
        if not contact_type:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, contact):
                data['contact_type'] = 'email'
            else:
                data['contact_type'] = 'phone'
        
        return data


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP and logging in"""
    contact = serializers.CharField(required=True)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6)
    
    # Optional fields for registration during first-time login
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    
    def validate_contact(self, value):
        """Validate contact format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        
        if re.match(email_pattern, value):
            return value
        elif re.match(phone_pattern, value.replace(' ', '').replace('-', '')):
            return value.replace(' ', '').replace('-', '')
        else:
            raise serializers.ValidationError("Invalid email or phone number format")


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'first_name', 'last_name', 
                  'is_verified', 'user_type', 'bio', 'avatar', 'created_at']
        read_only_fields = ['id', 'is_verified', 'created_at']
