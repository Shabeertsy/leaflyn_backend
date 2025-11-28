# Authentication API Documentation

## Overview
This API supports two authentication methods:
1. **Traditional Authentication**: Email/Phone + Password
2. **OTP-based Authentication**: Email/Phone + OTP (One-Time Password)

Base URL: `/api/auth/` (adjust according to your URL configuration)

---

## Endpoints

### 1. Traditional Registration
**POST** `/register/`

Register a new user with email/phone and password.

**Request Body:**
```json
{
  "email": "user@example.com",  // Optional if phone_number provided
  "phone_number": "+1234567890",  // Optional if email provided
  "password": "securepassword123",
  "first_name": "John",  // Optional
  "last_name": "Doe",  // Optional
  "bio": "User bio",  // Optional
  "user_type": "user"  // Optional, default: "user"
}
```

**Response (201 Created):**
```json
{
  "message": "User registered successfully."
}
```

---

### 2. Traditional Login
**POST** `/login/`

Login with email/phone and password.

**Request Body:**
```json
{
  "email": "user@example.com",  // Or use phone_number
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "phone_number": "+1234567890",
    "first_name": "John",
    "last_name": "Doe",
    "is_verified": true,
    "user_type": "user",
    "bio": "User bio",
    "avatar": null,
    "created_at": "2025-11-25T12:00:00Z"
  }
}
```

---

### 3. Send OTP
**POST** `/send-otp/`

Send OTP to email or phone number. If the user doesn't exist, they can register during OTP verification.

**Request Body:**
```json
{
  "contact": "user@example.com",  // Or phone number like "+1234567890"
  "contact_type": "email"  // Optional: "email" or "phone" (auto-detected if not provided)
}
```

**Response (200 OK):**
```json
{
  "message": "OTP sent to your email",
  "contact": "user@example.com",
  "contact_type": "email",
  "otp_code": "123456"  // Only in DEBUG mode
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": {
    "contact": ["Invalid email or phone number format"]
  }
}
```

---

### 4. Verify OTP
**POST** `/verify-otp/`

Verify OTP and login. If user doesn't exist, a new account will be created automatically.

**Request Body:**
```json
{
  "contact": "user@example.com",  // Or phone number
  "otp_code": "123456",
  "first_name": "John",  // Optional: for new users
  "last_name": "Doe"  // Optional: for new users
}
```

**Response (200 OK):**
```json
{
  "message": "Login successful",  // Or "Account created and logged in" for new users
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "phone_number": null,
    "first_name": "John",
    "last_name": "Doe",
    "is_verified": true,
    "user_type": "user",
    "bio": "",
    "avatar": null,
    "created_at": "2025-11-25T12:00:00Z"
  },
  "is_new_user": false
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Invalid OTP code"
}
```

**Error Response (400 Bad Request - Expired OTP):**
```json
{
  "error": "OTP has expired"
}
```

---

### 5. Resend OTP
**POST** `/resend-otp/`

Resend OTP to the same contact.

**Request Body:**
```json
{
  "contact": "user@example.com",  // Or phone number
  "contact_type": "email"  // Optional: auto-detected if not provided
}
```

**Response (200 OK):**
```json
{
  "message": "OTP sent to email",
  "contact": "user@example.com"
}
```

---

## Authentication Flow Examples

### Flow 1: OTP-based Login (New User)

1. **Send OTP**
   ```
   POST /send-otp/
   {
     "contact": "newuser@example.com"
   }
   ```

2. **Verify OTP (Creates account automatically)**
   ```
   POST /verify-otp/
   {
     "contact": "newuser@example.com",
     "otp_code": "123456",
     "first_name": "Jane",
     "last_name": "Smith"
   }
   ```
   
   Response includes JWT tokens and user data with `is_new_user: true`

### Flow 2: OTP-based Login (Existing User)

1. **Send OTP**
   ```
   POST /send-otp/
   {
     "contact": "+1234567890"
   }
   ```

2. **Verify OTP**
   ```
   POST /verify-otp/
   {
     "contact": "+1234567890",
     "otp_code": "654321"
   }
   ```
   
   Response includes JWT tokens and user data with `is_new_user: false`

### Flow 3: Traditional Registration + Login

1. **Register**
   ```
   POST /register/
   {
     "email": "user@example.com",
     "password": "securepass123",
     "first_name": "John",
     "last_name": "Doe"
   }
   ```

2. **Login**
   ```
   POST /login/
   {
     "email": "user@example.com",
     "password": "securepass123"
   }
   ```

---

## Using JWT Tokens

After successful login (either method), you'll receive:
- `access`: Short-lived token for API requests (60 minutes)
- `refresh`: Long-lived token to get new access tokens (7 days)

### Making Authenticated Requests

Include the access token in the Authorization header:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Refreshing Access Token

When the access token expires, use the refresh token to get a new one:

```
POST /api/token/refresh/
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## Phone Number Format

Phone numbers should be in international format:
- With country code: `+1234567890`
- Minimum 10 digits, maximum 15 digits
- Can include spaces or dashes (will be normalized): `+1 234-567-8900`

---

## Email Format

Standard email validation applies:
- Must contain `@` and domain
- Example: `user@example.com`

---

## OTP Details

- **Length**: 6 digits
- **Validity**: 5 minutes
- **Delivery**: Email or SMS (based on contact type)
- **Reuse**: Each OTP can only be used once
- **Multiple OTPs**: Requesting a new OTP invalidates previous unused OTPs

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created (Registration successful) |
| 400 | Bad Request (Invalid data) |
| 401 | Unauthorized (Invalid credentials) |
| 500 | Internal Server Error |

---

## Development vs Production

### Development (DEBUG=True)
- OTP codes are returned in the response for testing
- Emails are printed to console
- SMS messages are printed to console

### Production (DEBUG=False)
- OTP codes are NOT returned in the response
- Emails are sent via SMTP
- SMS messages are sent via configured provider (Twilio, etc.)

---

## SMS Configuration (Optional)

To enable SMS OTP, you need to:

1. Install SMS provider library (e.g., Twilio):
   ```bash
   pip install twilio
   ```

2. Add credentials to `settings.py`:
   ```python
   TWILIO_ACCOUNT_SID = 'your-account-sid'
   TWILIO_AUTH_TOKEN = 'your-auth-token'
   TWILIO_PHONE_NUMBER = 'your-twilio-phone-number'
   ```

3. Update `send_otp_sms()` function in `otp_utils.py` with actual Twilio implementation

---

## Email Configuration

### Development
Already configured to print emails to console.

### Production
Update `settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'noreply@leafin.com'
```

---

## Security Considerations

1. **HTTPS**: Always use HTTPS in production
2. **Rate Limiting**: Implement rate limiting on OTP endpoints to prevent abuse
3. **OTP Expiry**: OTPs expire after 5 minutes
4. **Password Strength**: Minimum 8 characters for password-based auth
5. **JWT Security**: Store tokens securely on client side
6. **Phone Verification**: Consider adding additional verification for sensitive operations

---

## Testing with Postman/cURL

### Example: Send OTP
```bash
curl -X POST http://localhost:8000/api/auth/send-otp/ \
  -H "Content-Type: application/json" \
  -d '{"contact": "test@example.com"}'
```

### Example: Verify OTP
```bash
curl -X POST http://localhost:8000/api/auth/verify-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "contact": "test@example.com",
    "otp_code": "123456",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### Example: Authenticated Request
```bash
curl -X GET http://localhost:8000/api/some-protected-endpoint/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```
