# ========================================
#     Mobile App API Views for Food Delivery
# ========================================

from django.contrib.auth import login
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from dashboard.models import (
    UserProfile, UserRole, Restaurant, OTPVerification, Slider, MenuItem, 
    MenuItemOption, MenuItemImage, CuisineType, Cart, Order, UserProfile, 
    OrderItem, RestaurantReview, Coupon, Newsletter, Contact, Notification, 
    CouponUsage, TaxRate, MenuSection, DeliveryPerson, DeliveryAssignment,
    DeliveryZone, RestaurantTiming, FoodTag, MenuItemReview
)
from django.contrib.auth.models import User
from decimal import Decimal
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
import random
from django.core.mail import send_mail
from django.db.models import F
from datetime import timedelta
from django.core.exceptions import ValidationError

# Configuration
STATIC_OTP = "1234"  # 4-digit static OTP for development
COUNTRY_CODE = "+977"



class SignupAPIView(APIView):
    """
    Signup API View for user registration with phone number and OTP verification
    """
    
    def validate_phone(self, phone):
        if not phone:
            raise ValidationError("Phone number is required")
        
        phone = phone.strip()
        
        if not phone.isdigit():
            raise ValidationError("Phone number must contain only digits")
        
        if len(phone) != 10:
            raise ValidationError("Phone number must be exactly 10 digits")
        
        if not phone.startswith(('98', '97')):
            raise ValidationError("Phone number must start with 98 or 97")
        
        return phone
    
    def validate_password(self, password):
        if not password:
            raise ValidationError("Password is required")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        
        if not any(char.isupper() for char in password):
            raise ValidationError("Password must contain at least one uppercase letter")
        
        return password
    
    def format_full_phone_number(self, phone):
        phone = re.sub(r'^(\+977|977)', '', phone)
        return f"{COUNTRY_CODE}{phone}"
    
    def mask_phone(self, phone):
        clean_phone = phone.replace('+977', '')
        if len(clean_phone) >= 10:
            masked = clean_phone[:2] + '*' * (len(clean_phone) - 4) + clean_phone[-2:]
            return f"+977{masked}"
        return phone
    
    def split_full_name(self, full_name):
        """
        Split full name into first_name and last_name.
        First two parts become first_name, last part becomes last_name.
        
        Examples:
        - "Hirta Bahadur Dhimal" -> first_name: "Hirta Bahadur", last_name: "Dhimal"
        - "John Doe" -> first_name: "John", last_name: "Doe"
        - "Hirta" -> first_name: "Hirta", last_name: ""
        """
        name_parts = full_name.strip().split()
        
        if not name_parts:
            return '', ''
        
        if len(name_parts) == 1:
            # Single name: "Hirta"
            return name_parts[0], ''
        elif len(name_parts) == 2:
            # Two names: "John Doe"
            return name_parts[0], name_parts[1]
        else:
            # Three or more names: "Hirta Bahadur Dhimal"
            # First name = first two parts, Last name = remaining parts
            first_name = ' '.join(name_parts[:2])  # First two words
            last_name = ' '.join(name_parts[2:])   # Rest as last name
            return first_name, last_name
    
    def is_production(self):
        import os
        return os.environ.get('DJANGO_ENV') == 'production'
    
    def post(self, request):
        try:
            phone = request.data.get('phone')
            password = request.data.get('password')
            full_name = request.data.get('full_name', '')
            email = request.data.get('email', '')
            
            # Validate required fields
            if not phone:
                return Response({
                    'success': False, 
                    'error': 'Phone number is required'
                }, status=400)
            
            if not password:
                return Response({
                    'success': False, 
                    'error': 'Password is required'
                }, status=400)
            
            if not full_name:
                return Response({
                    'success': False, 
                    'error': 'Full name is required'
                }, status=400)
            
            if not email:
                return Response({
                    'success': False, 
                    'error': 'Email is required'
                }, status=400)
            
            # Validate phone format
            try:
                phone = self.validate_phone(phone)
            except ValidationError as e:
                return Response({
                    'success': False, 
                    'error': str(e)
                }, status=400)
            
            # Validate password strength
            try:
                password = self.validate_password(password)
            except ValidationError as e:
                return Response({
                    'success': False, 
                    'error': str(e)
                }, status=400)
            
            full_phone = self.format_full_phone_number(phone)
            
            # Split full name into first_name and last_name
            first_name, last_name = self.split_full_name(full_name)
            
            # Check if phone already exists
            if UserProfile.objects.filter(phone=full_phone).exists():
                return Response({
                    'success': False, 
                    'error': 'User with this phone number already exists'
                }, status=400)
            
            if UserProfile.objects.filter(phone__endswith=phone).exists():
                return Response({
                    'success': False, 
                    'error': 'User with this phone number already exists'
                }, status=400)
            
            # Check if username exists
            if User.objects.filter(username=full_phone).exists():
                return Response({
                    'success': False, 
                    'error': 'User with this phone number already exists'
                }, status=400)
            
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                return Response({
                    'success': False, 
                    'error': 'User with this email already exists'
                }, status=400)
            
            # Create user
            user = User.objects.create_user(
                username=full_phone,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False
            )
            
            # Create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone = full_phone
            profile.email = email
            profile.save()
            
            # Generate OTP
            otp = STATIC_OTP
            
            otp_obj, _ = OTPVerification.objects.get_or_create(user=user)
            otp_obj.otp_code = otp
            otp_obj.created_at = timezone.now()
            otp_obj.save()
            
            return Response({
                'success': True,
                'message': f'We have sent a 4-digit verification code to {self.mask_phone(full_phone)}',
                'data': {
                    'phone': self.mask_phone(full_phone),
                    'email': email,
                    'full_name': full_name,
                    'first_name': first_name,
                    'last_name': last_name,
                    'user_id': user.id,
                    'requires_otp': True
                },
                'otp': otp if not self.is_production() else None
            }, status=201)
            
        except Exception as e:
            logger.error(f"Signup failed: {str(e)}", exc_info=True)
            return Response({
                'success': False, 
                'error': 'Signup failed. Please try again.'
            }, status=500)
    
    def send_sms_via_aakash(self, phone_number, otp):
        """
        Send SMS using Aakash SMS gateway (to be implemented later)
        """
        import requests
        
        # Aakash SMS API configuration
        api_key = "your_aakash_api_key"
        sender_id = "YourSenderID"
        api_url = "https://api.aakashsms.com/api/v1/sms/send"
        
        # Message with 4-digit OTP
        message = f"Your verification code is: {otp}"
        
        payload = {
            'api_key': api_key,
            'to': phone_number,
            'sender_id': sender_id,
            'message': message
        }
        
        try:
            response = requests.post(api_url, data=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"SMS sent successfully to {phone_number}")
                return response.json()
            else:
                logger.error(f"Aakash SMS failed with status: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Aakash SMS exception: {str(e)}")
            raise


class VerifySignupOTPAPIView(APIView):
    """
    Verify OTP for phone number verification during signup
    """
    
    def post(self, request):
        try:
            phone = request.data.get('phone')
            otp_code = request.data.get('otp_code')
            
            if not phone or not otp_code:
                return Response({
                    'success': False, 
                    'error': 'Phone number and OTP code are required'
                }, status=400)
            
            # Find user
            user = None
            full_phone = f"{COUNTRY_CODE}{phone}" if not phone.startswith('+') else phone
            
            profile = UserProfile.objects.filter(phone=full_phone).first()
            if profile:
                user = profile.user
            
            if not user:
                clean_phone = phone.replace(COUNTRY_CODE, '').strip()
                profile = UserProfile.objects.filter(phone__endswith=clean_phone).first()
                if profile:
                    user = profile.user
            
            if not user:
                return Response({
                    'success': False, 
                    'error': 'User not found with this phone number. Please signup first.'
                }, status=404)
            
            # Check if user is already active
            if user.is_active:
                return Response({
                    'success': False, 
                    'error': 'User is already verified'
                }, status=400)
            
            # Verify OTP
            try:
                otp_obj = OTPVerification.objects.get(user=user)
            except OTPVerification.DoesNotExist:
                return Response({
                    'success': False, 
                    'error': 'OTP not requested. Please signup again.'
                }, status=400)
            
            # Check OTP validity (10 minutes expiry)
            if otp_obj.created_at < timezone.now() - timedelta(minutes=10):
                return Response({
                    'success': False, 
                    'error': 'OTP has expired. Please request a new one.'
                }, status=400)
            
            # Verify OTP
            if otp_obj.otp_code != otp_code:
                return Response({
                    'success': False, 
                    'error': 'Invalid OTP code. Please try again.'
                }, status=400)
            
            # Activate user
            user.is_active = True
            user.save()
            
            # Clear OTP
            otp_obj.otp_code = None
            otp_obj.save()
            
            # Create user role if not exists
            UserRole.objects.get_or_create(user=user, defaults={'role': 'customer'})
            
            return Response({
                'success': True,
                'message': 'Phone number verified successfully! You can now login.',
                'data': {
                    'user_id': user.id,
                    'phone': user.profile.phone if hasattr(user, 'profile') else phone
                }
            }, status=200)
            
        except Exception as e:
            logger.error(f"OTP verification failed: {str(e)}", exc_info=True)
            return Response({
                'success': False, 
                'error': 'Verification failed. Please try again.'
            }, status=500)


class ResendSignupOTPAPIView(APIView):
    """
    Resend OTP for phone number verification during signup
    """
    
    def post(self, request):
        try:
            phone = request.data.get('phone')
            
            if not phone:
                return Response({
                    'success': False, 
                    'error': 'Phone number is required'
                }, status=400)
            
            # Clean phone number
            clean_phone = phone.replace(COUNTRY_CODE, '').strip()
            full_phone = f"{COUNTRY_CODE}{clean_phone}" if not clean_phone.startswith('+') else clean_phone
            
            # Find user
            user = None
            profile = UserProfile.objects.filter(phone=full_phone).first()
            if profile:
                user = profile.user
            
            if not user:
                profile = UserProfile.objects.filter(phone__endswith=clean_phone).first()
                if profile:
                    user = profile.user
            
            if not user:
                return Response({
                    'success': False, 
                    'error': 'User not found with this phone number'
                }, status=404)
            
            # Check if user is already active
            if user.is_active:
                return Response({
                    'success': False, 
                    'error': 'User is already verified'
                }, status=400)
            
            # Generate new 4-digit OTP
            otp = STATIC_OTP
            
            otp_obj, _ = OTPVerification.objects.get_or_create(user=user)
            otp_obj.otp_code = otp
            otp_obj.created_at = timezone.now()
            otp_obj.save()
            
            return Response({
                'success': True,
                'message': 'A new 4-digit verification code has been sent to your phone'
            }, status=200)
            
        except Exception as e:
            logger.error(f"Resend OTP failed: {str(e)}", exc_info=True)
            return Response({
                'success': False, 
                'error': 'Failed to resend OTP. Please try again.'
            }, status=500)


class SignupLoginAPIView(APIView):
    """
    Login API View for user authentication after signup using JWT
    Supports login with either Email or Phone
    """
    
    def post(self, request):
        try:
            identifier = request.data.get('identifier')  # Can be email or phone
            password = request.data.get('password')
            
            if not identifier or not password:
                return Response({
                    'success': False, 
                    'error': 'Email/Phone and password are required'
                }, status=400)
            
            user = None
            
            # Check if identifier is email
            if '@' in identifier and '.' in identifier:
                try:
                    user = User.objects.get(email=identifier, is_active=True)
                except User.DoesNotExist:
                    pass
            
            # If not found by email, try by phone
            if not user:
                clean_phone = identifier.replace(COUNTRY_CODE, '').strip()
                full_phone = f"{COUNTRY_CODE}{clean_phone}" if not clean_phone.startswith('+') else clean_phone
                
                # Search by full phone
                profile = UserProfile.objects.filter(phone=full_phone).first()
                if profile:
                    user = profile.user
                
                # Search by phone ending
                if not user:
                    profile = UserProfile.objects.filter(phone__endswith=clean_phone).first()
                    if profile:
                        user = profile.user
                
                # Search by username
                if not user:
                    user = User.objects.filter(username=full_phone).first()
            
            if not user:
                return Response({
                    'success': False, 
                    'error': 'Invalid email/phone or password'
                }, status=401)
            
            # Check if user is active
            if not user.is_active:
                return Response({
                    'success': False, 
                    'error': 'Account not verified. Please verify your phone number with the OTP sent to you.'
                }, status=401)
            
            # Check password
            if not user.check_password(password):
                return Response({
                    'success': False, 
                    'error': 'Invalid email/phone or password'
                }, status=401)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Get user role
            try:
                role = user.role.role
            except:
                role = 'customer'
            
            # Get user profile
            try:
                profile = user.profile
                user_phone = profile.phone
                gender = profile.gender
                avatar = profile.avatar.url if profile.avatar else None
                address = profile.address
                city = profile.city
            except:
                user_phone = identifier if identifier.startswith('+') else None
                gender = None
                avatar = None
                address = None
                city = None
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': f"{user.first_name} {user.last_name}".strip(),
                    'email': user.email,
                    'phone': user_phone,
                    'gender': gender,
                    'avatar': avatar,
                    'address': address,
                    'city': city,
                    'role': role
                }
            }, status=200)
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}", exc_info=True)
            return Response({
                'success': False, 
                'error': 'Login failed. Please try again.'
            }, status=500)


# ========= Utility Function to Clean HTML Text ==========
import re
from django.utils.html import strip_tags


def clean_ckeditor_text(html_text):
    """
    Clean CKEditor content and return readable plain text.
    Splits common product info fields onto separate lines.
    """
    if not html_text:
        return ""

    # Remove HTML tags
    text = strip_tags(html_text)

    # Replace <br> and tabs with newline
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = text.replace('\t', ' ')

    # Normalize spaces
    text = re.sub(r' +', ' ', text)

    # Split on common product info keywords and add newline
    # This works well if CKEditor saves everything in one paragraph
    keywords = ['Brand:', 'Manufacturer:', 'Country of Origin:', 'Sold by:', 'Volume:']
    for kw in keywords:
        text = text.replace(kw, f'\n{kw}')

    # Remove extra newlines
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join([line for line in lines if line])

    return text


# ========= Login =============
class LoginApiView(APIView):
    def post(self,request):
        try:
            email=request.data.get('email')
            password=request.data.get('password')
            try:
                user=User.objects.get(email=email,is_active=True)
                print(user)
            except User.DoesNotExist:
                return Response({'success':False,'error':'User not found'},status=400)
            if not user.check_password(password):
                return Response({'success':False,'error':'Incorrect password'},status=400)
            refresh=RefreshToken.for_user(user)
            return Response({
                'success':True,
                'refresh':str(refresh),
                'access':str(refresh.access_token),
                'user':{
                    'first_name':user.first_name,
                    'last_name':user.last_name,
                    'email':user.email,
                    'phone':user.profile.phone,
                    'gender':user.profile.gender,
                    'avatar':user.profile.avatar.url if user.profile.avatar else None,
                    'address':user.profile.address,
                    'city':user.profile.city  
                }})
            
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)


import logging
from django.utils import timezone
logger = logging.getLogger(__name__)

# ============= Logout =============
class LogoutView(APIView):
    def post(self,request):
        try:
            refresh_token=request.data.get('refresh')
            if not refresh_token:
                return Response({'success':False,'error':str(e)})
            token=RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"User {request.user} logged out successfully.")
            return Response({'success':True,'message':'Logout successful'},status=200)
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({'success':False,'error':str(e)},status=400)

import logging
logger = logging.getLogger(__name__)

# ============ Register =============
class RegisterApiView(APIView):
    def post(self,request):
        try:
            first_name=request.data.get('first_name')
            last_name=request.data.get('last_name')
            email=request.data.get('email')
            password=request.data.get('password')
            if User.objects.filter(email=email,is_active=True).exists():
                return Response({'success':False,'error':"User already found"},status=400)
            
            user=User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False
            )
            otp=str(random.randint(100000,999999))
            otp_obj,_=OTPVerification.objects.get_or_create(user=user)
            otp_obj.otp_code=otp
            otp_obj.save()
            send_mail(
                subject="Your NFC Account OTP Verification Code",
                message=f"Hello {first_name},\n\nYour OTP code is: {otp}.",
                from_email="info.nfc026@gmail.com",
                recipient_list=[email],
                fail_silently=False
            )
            return Response({'success':True,'message':'User registered successfully. Please verify OTP sent to your email.'},status=201)    
        except Exception as e:
            logger.error(f"Registration failed: {str(e)}", exc_info=True)
            return Response({'success':False,'error':str(e)})


# =========== Resend Otp ===========
class  ResendOtpApiView(APIView):
    def post(self,request):
        try:
            email=request.data.get('email')
            try:
                user=User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'success':False,'error':'User not found'},status=400)

            otp=str(random.randint(100000,999999))
            otp_obj,_=OTPVerification.objects.get_or_create(user=user)
            otp_obj.otp_code=otp
            otp_obj.save()
            
            send_mail(
                subject="Your NFC OTP Verification Code",
                message=f"Hello {user.first_name},\n\nYour OTP code is: {otp}.",
                from_email="info.nfc026@gmail.com",
                recipient_list=[email],
                fail_silently=False
            )
            return Response({'success':True,'message':'Otp resend successfully'},status=200)
            
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)
        

# ============ Register =============
# class RegisterApiView(APIView):
#     def post(self, request):
#         try:
#             first_name = request.data.get('first_name')
#             last_name = request.data.get('last_name')
#             email = request.data.get('email')
#             password = request.data.get('password')

#             # Check if active user already exists
#             if User.objects.filter(email=email, is_active=True).exists():
#                 return Response({'success': False, 'error': "User already exists"}, status=400)

#             if User.objects.filter(email=email,is_active=False).exists():
#                 user=User.objects.get(email=email)
#                 user.first_name=first_name
#                 user.last_name=last_name
#                 user.save()
#             else:
#                 user = User.objects.create_user(
#                     username=email,
#                     email=email,
#                     password=password,
#                     first_name=first_name,
#                     last_name=last_name,
#                     is_active=False
#                 )

#             # Generate OTP and save
#             otp = str(random.randint(100000, 999999))
#             otp_obj, _ = OTPVerification.objects.get_or_create(user=user)
#             otp_obj.otp_code = otp
#             otp_obj.save()

#             # Send OTP via email
#             send_mail(
#                 subject="Your Hello Bajar OTP Verification Code",
#                 message=f"Hello {first_name},\n\nYour OTP code is: {otp}.",
#                 from_email="hellobajar@gmail.com",
#                 recipient_list=[email],
#                 fail_silently=False
#             )

#             return Response({'success': True, 'message': 'User registered successfully. Please verify OTP sent to your email.'}, status=201)

#         except Exception as e:
#             return Response({'success': False, 'error': str(e)}, status=400)


# =========== Verify OTP =============
class VerifyOtpApiView(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            otp_code = request.data.get('otp_code')
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'success': False, 'error': 'User not found'}, status=400)

            if user.is_active:
                return Response({'success': False, 'error': 'User is already exists'}, status=400)

            try:
                otp_obj = OTPVerification.objects.get(user=user)
            except OTPVerification.DoesNotExist:
                return Response({'success': False, 'error': 'OTP not found. Please request a new one.'}, status=400)
            if otp_obj.otp_code != otp_code:
                return Response({'success': False, 'error': 'Invalid OTP code'}, status=400)

            user.is_active = True
            user.save()
            UserProfile.objects.create(user=user)
            UserRole.objects.create(user=user, role='customer')
            otp_obj.delete()

            return Response({'success': True, 'message': 'OTP verified successfully. Your account is now active.'}, status=200)

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ========== Forget Password Verify OTP =============
class ForgetPasswordVerifyOtpApiView(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            otp_code = request.data.get('otp_code')
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'success': False, 'error': 'User not found'}, status=400)

            try:
                otp_obj = OTPVerification.objects.get(user=user)
            except OTPVerification.DoesNotExist:
                return Response({'success': False, 'error': 'OTP not found. Please request a new one.'}, status=400)
            if otp_obj.otp_code != otp_code:
                return Response({'success': False, 'error': 'Invalid OTP code'}, status=400)
            
            access_token = str(RefreshToken.for_user(user).access_token)
            return Response({'success': True,'access':access_token, 'message': 'OTP verified successfully. You can now reset your password.'}, status=200)

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)
        



# ========== Reset Password ==============
class ResetPasswordApiView(APIView):
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        try:
            new_password = request.data.get('new_password')
            confirm_password = request.data.get('confirm_password')
            try:
                user = User.objects.get(email=request.user.email)
            except User.DoesNotExist:
                return Response({'success': False, 'error': 'User not found'}, status=400)

            if new_password != confirm_password:
                return Response({'success': False, 'error': 'Passwords do not match'}, status=400)

            user.set_password(new_password)
            user.save()

            return Response({'success': True, 'message': 'Password reset successfully'}, status=200)

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)
    
        
# ========== Forget Password =============
class ForgetPasswordApiView(APIView):
    def post(self,request):
        try:
            email=request.data.get('email')
            try:
                user=User.objects.get(email=email,is_active=True)
            except User.DoesNotExist:
                return Response({'success':False,'error':'No account found with that email'},status=400)
            otp=str(random.randint(100000,999999))
            otp_obj,_=OTPVerification.objects.get_or_create(
                user=user    
            )
            otp_obj.otp_code=otp
            otp_obj.save()
            send_mail(
                subject="Your Password Reset OTP",
                message=f"Your OTP for password reset is {otp} .",
                from_email="hellobajar@gmail.com",
                recipient_list=[email],
                fail_silently=False
            )
            return Response({'success':True,'message':'OTP sent to your email for password reset.'},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)





# ====== Category API View ======
class CategoryApiView(APIView):
    def get(self, request):
        try:
            categories = Category.objects.filter(is_active=True)
            category_data = []
            for category in categories:
                category_data.append({
                    'id': category.id,
                    'name': category.name,
                    'image': category.image.url if category.image else None,
                    'subcategories': [
                        {
                            'id': subcat.id,
                            'name': subcat.name,
                        } for subcat in category.subcategories.all()
                    ]
                })
            return Response({'success': True, 'categories': category_data}, status=200)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)



    
    
# ====== Home API View ======
class HomeApiView(APIView):

    def get(self,request):
        try:
            city = request.GET.get('city', '').strip()
            categorys=Category.objects.filter(is_active=True,is_featured=True)[:10]
            
            featured_products=Product.objects.filter(is_active=True,is_featured=True)
            best_offers = Product.objects.filter(
                is_active=True,
                price__lt=F('cost_price') * 0.75  # Price less than 75% of cost price = >25% discount
            )
            if city:
                featured_products = featured_products.filter(vendor__city__iexact=city)
                best_offers = best_offers.filter(vendor__city__iexact=city)
            
            featured_products = featured_products.order_by('-created_at')[:20]
            best_offers = best_offers.order_by('-created_at')[:20]
           
            sliders=Slider.objects.filter(is_active=True).order_by('-created_at')
            category_data=[]
            featured_product_data=[]
            best_offers_product_data=[]
            slider_data=[]
            for slider in sliders:
                slider_data.append({
                    'id':slider.id,
                    'image':slider.image.url,
                })
            for category in categorys:
                category_data.append({
                    'id':category.id,
                    'name':category.name,
                    'image':category.image.url,
                })
            for product in featured_products:
                featured_product_data.append({
                    'id':product.id,
                    'name':product.name,
                    'price':product.price,
                    'cost_price':product.cost_price,
                    'in_stock':product.in_stock,
                    'category':product.category.name,
                    'main_image':product.main_image.url,
                })
            
            for product in best_offers:
                best_offers_product_data.append({
                    'id':product.id,
                    'name':product.name,
                    'price':product.price,
                    'cost_price':product.cost_price,
                    'in_stock':product.in_stock,
                    'category':product.category.name,
                    'main_image':product.main_image.url,
                })
            return Response({'success':True,'sliders':slider_data,'categories':category_data,'featured_products':featured_product_data,'best_offers_products':best_offers_product_data},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)



# =============== All Collections ==============
class AllCollectionsApiView(APIView):
    def get(self,request):
        city = request.GET.get('city', '').strip()
        products=Product.objects.filter(is_active=True)
        
        if city:
            products = products.filter(vendor__city__iexact=city)
        
        products = products.order_by('-created_at')
  
        product_data=[]
        for product in products:
            product_data.append({
                'id':product.id,
                'name':product.name,
                'price':product.price,
                'cost_price':product.cost_price,
                'in_stock':product.in_stock,
                'category':product.category.name if product.category else None,
                'main_image':product.main_image.url if product.main_image else None,
            })
        return Response({'success':True,'products':product_data},status=200)
    



# ============= New Arrivals =============
class NewArrivalsApiView(APIView):
    def get(self,request):
        one_month_ago=timezone.now()-timezone.timedelta(days=29)
        city = request.GET.get('city', '').strip()
        one_month_ago=timezone.now()-timezone.timedelta(days=29)
        new_arrivals=Product.objects.filter(is_active=True,created_at__gte=one_month_ago)
        
        if city:
            new_arrivals = new_arrivals.filter(vendor__city__iexact=city)
        
        new_arrivals = new_arrivals.order_by('-created_at')
        product_data=[]
        for product in new_arrivals:
            product_data.append({
                'id':product.id,
                'name':product.name,
                'price':product.price,
                'cost_price':product.cost_price,
                'in_stock':product.in_stock,
                'category':product.category.name if product.category else None,
                'main_image':product.main_image.url if product.main_image else None,
            })
        return Response({'success':True,'new_arrivals':product_data},status=200)
    



# ==========Vendor Page =============
class VendorsApiView(APIView):
    def get(self,request):
        city=  request.GET.get('city', '').strip()
        vendors=Vendor.objects.filter(is_active=True)
        if city:
            vendors = vendors.filter(city__iexact=city)
                 
    
        vendors = vendors.order_by('-created_at')
        vendor_data=[]
        for vendor in vendors:
            vendor_data.append({
                'id':vendor.id,
                'name':vendor.shop_name,
                'banner':vendor.shop_banner.url if vendor.shop_banner else None,
                'logo':vendor.shop_logo.url if vendor.shop_logo else None,
                'description':vendor.description,
            })
        return Response({'success':True,'vendors':vendor_data},status=200)
    
    

class VendorProductsDetails(APIView):
    def get(self,request,vendor_id):
        try:
            vendor=get_object_or_404(Vendor,id=vendor_id)
            products=Product.objects.filter(vendor=vendor)
            product_data=[]
            for product in products:
                product_data.append({
                    'id':product.id,
                    'name':product.name,
                    'price':product.price,
                    'cost_price':product.cost_price,
                    'in_stock':product.in_stock,
                    'category':product.category.name if product.category else None,
                    'main_image':product.main_image.url if product.main_image else None,
                })
            return Response({'success':True,'vendor':vendor.shop_name,'products':product_data},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)
        
        
# ========== Filter Product Category  Brand  ,Price =============
class FilterProductsApiView(APIView):
    def get(self, request):
        try:
            city = request.GET.get('city', '').strip()
            category_name = request.GET.get('category_name', '')  
            brand_name = request.GET.get('brand_name', '')        
            min_price = request.GET.get('min_price', None)
            max_price = request.GET.get('max_price', None)

            products = Product.objects.all()
            
            if city:
                products = products.filter(vendor__city__iexact=city)
            
            if category_name:
                products = products.filter(category__name__icontains=category_name)

            if brand_name:
                products = products.filter(brand__name__icontains=brand_name)

            if min_price is not None:
                products = products.filter(price__gte=float(min_price))

            if max_price is not None:
                products = products.filter(price__lte=float(max_price))

            product_data = []
            for product in products:
                product_data.append({
                    'id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'cost_price': product.cost_price,
                    'in_stock': product.in_stock,
                    'category': product.category.name if product.category else None,
                    'main_image': product.main_image.url if product.main_image else None,
                })

            return Response({'success': True, 'products': product_data}, status=200)

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)

from django.db.models import Q

# # ========== Search Products =============
class SearchProductsApiView(APIView):
    def get(self, request):
        try:
            query = request.GET.get('query', '').strip()
            city = request.GET.get('city', '').strip()

            filters = Q()

            if query:
                filters |= Q(name__icontains=query)
                filters |= Q(description__icontains=query)
                filters |= Q(brand__name__icontains=query)

                # if query is number → search by price
                if query.isdigit():
                    filters |= Q(price=query)

            products = Product.objects.filter(filters).distinct()

            if city:
                products = products.filter(vendor__city__iexact=city)

            product_data = []
            for product in products:
                product_data.append({
                    'id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'cost_price': product.cost_price,
                    'in_stock': product.in_stock,
                    'category': product.category.name if product.category else None,
                    'brand': product.brand.name if product.brand else None,
                    'main_image': product.main_image.url if product.main_image else None,
                })

            return Response(
                {'success': True, 'products': product_data},
                status=200
            )

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=400
            )
# ============ Product Details =============
class ProductDetailsApiView(APIView):
    def get(self, request, id):
        try:

            product = get_object_or_404(Product, pk=id)
            
            product_data = {
                'id': product.id,
                'name': product.name,
                'main_image':product.main_image,
                'description': clean_ckeditor_text(product.description),
                'price': product.price,
                'brand': product.brand.name if product.brand else None,
                'cost_price': product.cost_price,
                'in_stock': product.in_stock,
                'category': product.category.name if product.category else None,
                'main_image': product.main_image.url if product.main_image else None,
                'shipping_cost':product.shipping_cost,
                'estimated_delivery_days':product.estimated_delivery_days,
                'vendor':product.vendor.shop_name if product.vendor else None,
                
            }

            # Get product gallery images
            images = ProductImage.objects.filter(product=product)
            product_data['gallery'] = [img.image.url for img in images if img.image]

            # Get product variants
            variants = ProductVariant.objects.filter(product=product)
            variant_list = []
            for v in variants:
                variant_list.append({
                    'id': v.id,
                    'variant_type': v.get_variant_type_display(),  # shows "Size", "Color", etc.
                    'name': v.name,
                    'price_adjustment': v.price_adjustment,
                })
            product_data['variants'] = variant_list
            return Response({'success': True, 'product': product_data}, status=200)

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============ Category Products =============
class CategoryProductsApiView(APIView):
    def get(self,request,category_id):
        try:
            city = request.GET.get('city', '').strip()
            category=get_object_or_404(Category,id=category_id)
            products=Product.objects.filter(category=category)
            
            if city:
                products = products.filter(vendor__city__iexact=city)
            
            product_data=[]
            for product in products:
                product_data.append({
                    'id':product.id,
                    'name':product.name,
                    'price':product.price,
                    'cost_price':product.cost_price,
                    'in_stock':product.in_stock,
                    'category':product.category.name,
                    'main_image':product.main_image.url,
                })
            return Response({'success':True,'featured_category':category.name,'products':product_data},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)

# class SubCategoryProductsApiView(APIView):
#     def get(self,request,subcategory_id):
#         try:
#             city = request.GET.get('city', '').strip()
#             subcategory=get_object_or_404(SubCategory,id=subcategory_id)
#             products=Product.objects.filter(subcategory=subcategory)
            
#             if city:
#                 products = products.filter(vendor__city__iexact=city)
#             product_data=[]
#             for product in products:
#                 product_data.append({
#                     'id':product.id,
#                     'name':product.name,
#                     'price':product.price,
#                     'cost_price':product.cost_price,
#                     'in_stock':product.in_stock,
#                     'category':product.category.name,
#                     'main_image':product.main_image.url if product.main_image else None,
#                 })
#             return Response({'success':True,'subcategory':subcategory.name,'products':product_data},status=200)
#         except Exception as e:
#             return Response({'success':False,'error':str(e)},status=400)
        
        
    

# ========== Add to Cart =============
class AddToCartApiView(APIView):

    authentication_classes=[JWTAuthentication]
    
    def post(self,request):
        try:
            print(request.data)
            user=request.user
            print(user)
            product_id=request.data.get('product_id')
            quantity=request.data.get('quantity',1)
            product=get_object_or_404(Product,id=product_id)
            if not product.in_stock:
                return Response({'success':False,'error':'Product is out of stock'},status=400)
            cart_item,created=Cart.objects.get_or_create(user=user,product=product)
            if not created:
                cart_item.quantity+=quantity
            else:
                cart_item.quantity=quantity
            cart_item.save()
            return Response({'success':True,'message':'Product added to cart successfully.'},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)
        
        
        

# ========== View Cart =============
class ViewCartApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        try:
            user = request.user
            cart_items = Cart.objects.filter(user=user).select_related('menu_item', 'menu_item__restaurant')
            cart_data = []

            # Group items by restaurant
            restaurant_groups = {}
            for item in cart_items:
                restaurant = item.menu_item.restaurant
                if restaurant not in restaurant_groups:
                    restaurant_groups[restaurant] = []
                restaurant_groups[restaurant].append(item)

            # Calculate total delivery: max per restaurant, then sum
            total_delivery = 0
            for restaurant, items in restaurant_groups.items():
                # Use delivery_fee or similar field from restaurant or menu_item
                delivery_fee = getattr(restaurant, 'delivery_fee', 0) or 0
                total_delivery += delivery_fee

            for item in cart_items:
                delivery_fee = getattr(item.menu_item.restaurant, 'delivery_fee', 0) or 0
                cart_data.append({
                    'id': item.id,
                    'menu_item_id': item.menu_item.id,
                    'menu_item_name': item.menu_item.name,
                    'image': item.menu_item.image.url if item.menu_item.image else None,
                    'quantity': item.quantity,
                    'price': float(item.menu_item.price),
                    'total_price': float(item.menu_item.price * item.quantity),
                    'delivery_fee': float(delivery_fee)
                })
            return Response({'success': True, 'cart_items': cart_data, 'total_delivery': float(total_delivery)}, status=200)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)
        
        
        
 
# ========== Update Cart Item =============
class UpdateCartItemApiView(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes=[JWTAuthentication]
    
    def post(self,request):
        try:
            user=request.user
            cart_item_id=request.data.get('cart_item_id')
            cart_item=get_object_or_404(Cart,id=cart_item_id,user=user)
            quantity=request.data.get('quantity',1)
            
            if cart_item.menu_item.in_stock < quantity:
                return Response({'success':False,'error':'Requested quantity exceeds available stock.'},status=400)
            
            cart_item.quantity=quantity
            cart_item.save()
            return Response({'success':True,'message':'Cart item updated successfully.'},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)
        
        
# ========== Remove from Cart =============
class RemoveFromCartApiView(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes=[JWTAuthentication]
    
    def post(self,request):
        try:
            user=request.user
            cart_item_id=request.data.get('cart_item_id')
            cart_item=get_object_or_404(Cart,id=cart_item_id,user=user)
            cart_item.delete()
            return Response({'success':True,'message':'Cart item removed successfully.'},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)       
    


# ============= Users Profile API View =============
class CustomerProfileApiView(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes=[JWTAuthentication]
    
    def get(self,request):
        try:
            user=request.user
            profile=user.profile
            profile_data={
                'first_name':user.first_name,
                'last_name':user.last_name,
                'email':user.email,
                'phone':profile.phone,
                'gender':profile.gender,   
                'avatar':profile.avatar.url if profile.avatar else None,
                'address':profile.address,
                'city':profile.city,
            }
            return Response({'success':True,'profile':profile_data},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)

class EditCustomerProfileApiView(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes=[JWTAuthentication]
    
    def post(self,request):
        try:
            user=request.user
            profile=user.profile
            user.first_name=request.data.get('first_name',user.first_name)
            user.last_name=request.data.get('last_name',user.last_name)
            user.email=request.data.get('email',user.email)
            profile.phone=request.data.get('phone',profile.phone)
            if 'avatar' in request.FILES:  
                profile.avatar = request.FILES['avatar']
            
            profile .gender=request.data.get('gender',profile.gender)
            profile.address=request.data.get('address',profile.address) 
            profile.city=request.data.get('city',profile.city)
            user.save()
            profile.save()
            return Response({'success':True,'message':'Profile updated successfully.'},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)
        
  
# ============= Order History API View =============
class CustomerOrderHistoryApiView(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes=[JWTAuthentication]
    
    def get(self,request):
        try:
            user=request.user
            orders=Order.objects.filter(user=user).order_by('status','-created_at')
            order_data=[]
            for order in orders:
                order_data.append({
                    'id':order.id,
                    'products':[{
                        'product_name':item.menu_item.name,
                        'main_image':item.menu_item.image.url if item.menu_item.image else None,
                        'quantity':item.quantity,
                        'price':item.price,
                    } for item in OrderItem.objects.filter(order=order)],
                    'order_number':order.order_number,
                    'total_amount':order.total,
                    'status':order.status,
                    'created_at':order.created_at,
                })
            return Response({'success':True,'orders':order_data},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)    



# ============= Order Details API View =============
class CustomerOrderDetailsApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, order_id):
        try:
            user = request.user
            order = get_object_or_404(Order, id=order_id, user=user)
            
            order_data = {
                'id': order.id,
                'products': [
                    {
                        'product_name': item.menu_item.name,
                        'main_image': item.menu_item.image.url if item.menu_item.image else None,
                        'quantity': item.quantity,
                        'price': item.price,
                        'shop_name': item.menu_item.restaurant.restaurant_name if item.menu_item.restaurant else None,
                    } 
                    for item in order.items.all() 
                ],
                
                'order_number': order.order_number,
                'subtotal': order.subtotal,
                'shipping_cost': order.shipping_cost,
                'shipping_full_name': order.full_name,
                'shipping_phone': order.phone,
                'shipping_address': order.address,
                'shiiping_city': order.city,
                'shipping_province': order.province,
                'shipping_email': order.email,
                'shipping_postal_code': order.postal_code,
                'discount': order.discount,
                'tax_percentage': order.tax_percentage,
                'tax_amount': order.tax_amount,
                'total_amount': order.total,
                'estimated_delivery_date': order.estimated_delivery_date,
                'status': order.status,
                'created_at': order.created_at,
            }
            return Response({'success': True, 'order': order_data}, status=200)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)
      

# ============= Change Password API View =============
class ChangePasswordApiView(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes=[JWTAuthentication]
    
    def post(self,request):
        try:
            user=request.user
            current_password=request.data.get('current_password')
            new_password=request.data.get('new_password')
            confirm_password=request.data.get('confirm_password')
            if not user.check_password(current_password):
                return Response({'success':False,'error':'Current password is incorrect.'},status=400)
            if new_password != confirm_password:
                return Response({'success':False,'error':'New passwords do not match.'},status=400)
            user.set_password(new_password)
            user.save()
            return Response({'success':True,'message':'Password changed successfully.'},status=200)
        except Exception as e:
            return Response({'success':False,'error':str(e)},status=400)


# ============= Checkout API View =============


class CheckoutApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        user = request.user
        cart_items = Cart.objects.filter(user=user).select_related('menu_item', 'menu_item__restaurant')
        if not cart_items.exists():
            return Response({'success': False, 'error': 'Cart is empty.'}, status=400)
        
        full_name = request.data.get('full_name')
        phone = request.data.get('phone')
        email = request.data.get('email')
        address = request.data.get('address')
        city = request.data.get('city')
        province = request.data.get('province')
        payment_method = request.data.get('payment_method', 'cod')
        coupon_code = request.data.get('coupon_code')
        
        subtotal = sum(item.get_total_price() for item in cart_items)
        
        # Calculate delivery fee per restaurant
        restaurant_groups = {}
        for item in cart_items:
            restaurant = item.menu_item.restaurant
            if restaurant not in restaurant_groups:
                restaurant_groups[restaurant] = []
            restaurant_groups[restaurant].append(item)
        
        total_delivery_fee = Decimal('0.00')
        for restaurant, items in restaurant_groups.items():
            delivery_fee = getattr(restaurant, 'delivery_fee', Decimal('0.00')) or Decimal('0.00')
            total_delivery_fee += delivery_fee
        
        discount = Decimal('0.00')
        tax_amount = Decimal('0.00')
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                is_valid, msg = coupon.is_valid(user=user, cart_items=cart_items)
                if is_valid:
                    discount = coupon.get_discount_amount(subtotal)
                else:
                    return Response({'success': False, 'error': msg}, status=400)
            except Coupon.DoesNotExist:
                return Response({'success': False, 'error': 'Invalid coupon code.'}, status=400)

        tax_rate = TaxRate.objects.first()
        if tax_rate:
            tax_amount = ((subtotal + total_delivery_fee) * tax_rate.tax / 100).quantize(Decimal('0.01'))

        total = subtotal + total_delivery_fee - discount + tax_amount

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=user, full_name=full_name, phone=phone, email=email,
                    address=address, city=city, province=province,
                    subtotal=subtotal, shipping_cost=total_delivery_fee,
                    discount=discount, tax_amount=tax_amount, total=total,
                    payment_method=payment_method, coupon=coupon
                )
                
                for item in cart_items:
                    order_item = OrderItem.objects.create(
                        order=order,
                        menu_item=item.menu_item,
                        quantity=item.quantity,
                        price=item.get_item_price()
                    )
                    # If you have options/variants, set them here
                    # order_item.options.set(item.options.all())
                    item.menu_item.in_stock = F('in_stock') - item.quantity
                    item.menu_item.save()
                
                if coupon:
                    CouponUsage.objects.create(user=user, coupon=coupon, order=order)
                    coupon.used_count += 1
                    coupon.save()
                
                Notification.objects.create(
                    user=user,
                    notification_type='order',
                    title=f"Order {order.order_number} Placed",
                    message=f"Your order {order.order_number} has been placed successfully."
                )
                
                cart_items.delete()
            
            return Response({'success': True, 'message': 'Order placed successfully.', 'order_id': order.order_number}, status=201)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)
        
        

# ============= Product Reviews API View =============
class ProductReviewsApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, product_id):
        try:
            reviews = Review.objects.filter(product_id=product_id).order_by('-created_at')
            review_data = [{
                'id': r.id,
                'user': f"{r.user.first_name} {r.user.last_name}",
                'rating': r.rating,
                'comment': r.comment,
                'created_at': r.created_at.strftime("%Y-%m-%d %H:%M:%S")
            } for r in reviews]
            
            return Response({'success': True, 'reviews': review_data}, status=200)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)

    def post(self, request, product_id):
        try:
            user = request.user
            rating = int(request.data.get('rating'))
            comment = request.data.get('comment', '')

            if rating < 1 or rating > 5:
                return Response({'success': False, 'error': 'Rating must be between 1 and 5'}, status=400)

            review, created = Review.objects.update_or_create(
                user=user,
                product_id=product_id,
                defaults={'rating': rating, 'comment': comment}
            )

            return Response({'success': True, 'message': 'Review submitted successfully.'}, status=201)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)
        
        
        

# ============= Coupon Verify API View =============
class CouponVerifyApiView(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes=[JWTAuthentication]
    
    def post(self, request):
        try:
            code = request.data.get('code')
            if not code:
                 return Response({'success':False, 'error':'Coupon code is required'}, status=400)
            
            try:
                coupon = Coupon.objects.get(code=code)
            except Coupon.DoesNotExist:
                return Response({'success':False, 'error':'Invalid coupon code'}, status=400)
            
            user = request.user
            cart_items = Cart.objects.filter(user=user)
            
            is_valid, message = coupon.is_valid(user=user, cart_items=cart_items)
            
            if is_valid:
                # Calculate potential discount
                subtotal = sum(item.get_total_price() for item in cart_items)
                discount = coupon.get_discount_amount(subtotal)
                return Response({
                    'success':True, 
                    'message': 'Coupon applied successfully',
                    'discount_amount': discount,
                    'code': code
                }, status=200)
            else:
                return Response({'success':False, 'error': message}, status=400)
                
        except Exception as e:
            return Response({'success':False, 'error':str(e)}, status=400)


# ============= Newsletter API View =============
class NewsletterApiView(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            if not email:
                return Response({'success':False, 'error':'Email is required'}, status=400)
            
            if Newsletter.objects.filter(email=email).exists():
                return Response({'success':False, 'error':'Email already subscribed'}, status=400)
            
            Newsletter.objects.create(email=email)
            return Response({'success':True, 'message':'Subscribed successfully'}, status=201)
        except Exception as e:
            return Response({'success':False, 'error':str(e)}, status=400)


# ============= Contact API View =============
class ContactApiView(APIView):
    def post(self, request):
        try:
            name = request.data.get('name')
            email = request.data.get('email')
            subject = request.data.get('subject')
            message = request.data.get('message')
            
            if not all([name, email, message]):
                return Response({'success':False, 'error':'Name, email and message are required'}, status=400)
            
            Contact.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            return Response({'success':True, 'message':'Message sent successfully'}, status=201)
        except Exception as e:
            return Response({'success':False, 'error':str(e)}, status=400)


# ============= Notification API View =============
class NotificationApiView(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes=[JWTAuthentication]
    
    def get(self, request):
        try:
            notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
            data = []
            for n in notifications:
                data.append({
                    'id': n.id,
                    'type': n.notification_type,
                    'title': n.title,
                    'message': n.message,
                    'link': n.link,
                    'is_read': n.is_read,
                    'created_at': n.created_at
                })
            return Response({'success':True, 'notifications': data}, status=200)
        except Exception as e:
            return Response({'success':False, 'error':str(e)}, status=400)




# ================================================================
#     DELIVERY PERSON API - Mobile App
# ================================================================


class DeliveryLoginApiView(APIView):
    def post(self,request):
        try:
            email=request.data.get('email')
            password = request.data.get('password')

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'success':False, 'error':'Invalid email or password'},status=400)
            
            if not user.check_password(password):
                return Response({'success':False,'error': 'Invalid email or password'},status=400)
            
            try:
                delivery_person = DeliveryPerson.objects.get(user=user)
            except DeliveryPerson.DoesNotExist:
                return Response({'success':False , 'error':'You are not a delivery person'},status=400)
            
            if not delivery_person.is_active:
                return Response({'success':False, 'error':'Your account is inactive'},status=400)
            
            refresh = RefreshToken.for_user(user)   

            return Response({
                'success': True,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'delivery_person': {
                    'id': delivery_person.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'phone': delivery_person.phone,
                    'address': delivery_person.address,
                    'is_active': delivery_person.is_active,
                }
            }, status=200)
        

        except Exception as e:
            return Response({'success':False, 'error': str(e)}, status=400)


# ============= Delivery Person Logout =============
class DeliveryLogoutApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'success': False, 'error': 'Refresh token required'}, status=400)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({'success': True, 'message': 'Logout successful'}, status=200)
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= Get Delivery Person Profile =============
class DeliveryProfileApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        try:
            user = request.user
            delivery_person = DeliveryPerson.objects.get(user=user)
            
            profile_data = {
                'id': delivery_person.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': delivery_person.phone,
                'address': delivery_person.address,
                'is_active': delivery_person.is_active,
            }
            
            return Response({'success': True, 'profile': profile_data}, status=200)
        
        except DeliveryPerson.DoesNotExist:
            return Response({'success': False, 'error': 'Delivery person profile not found'}, status=404)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= Update Delivery Person Profile =============
class UpdateDeliveryProfileApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        try:
            user = request.user
            delivery_person = DeliveryPerson.objects.get(user=user)
            
            # Update user fields
            user.first_name = request.data.get('first_name', user.first_name)
            user.last_name = request.data.get('last_name', user.last_name)
            user.save()
            
            # Update delivery person fields
            delivery_person.phone = request.data.get('phone', delivery_person.phone)
            delivery_person.address = request.data.get('address', delivery_person.address)
            delivery_person.save()
            
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'profile': {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone': delivery_person.phone,
                    'address': delivery_person.address,
                }
            }, status=200)
        
        except DeliveryPerson.DoesNotExist:
            return Response({'success': False, 'error': 'Delivery person profile not found'}, status=404)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= List Delivery Assignments =============
class DeliveryAssignmentsListApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        try:
            user = request.user
            delivery_person = DeliveryPerson.objects.get(user=user)
            
            assignments = DeliveryAssignment.objects.filter(
                delivery_person=delivery_person
            ).order_by('-assigned_at')
            
            assignments_data = []
            for assignment in assignments:
                assignments_data.append({
                    'id': assignment.id,
                    'order_number': assignment.order.order_number,
                    'customer_name': assignment.order.full_name,
                    'customer_phone': assignment.order.phone,
                    'address': assignment.order.address,
                    'total': str(assignment.order.total),
                    'status': assignment.status,
                    'assigned_at': assignment.assigned_at.strftime('%Y-%m-%d %H:%M') if assignment.assigned_at else None,
                })
            
            return Response({
                'success': True,
                'assignments': assignments_data
            }, status=200)
        
        except DeliveryPerson.DoesNotExist:
            return Response({'success': False, 'error': 'Delivery person not found'}, status=404)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= Get Assignment Details =============
class DeliveryAssignmentDetailApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request, assignment_id):
        try:
            user = request.user
            delivery_person = DeliveryPerson.objects.get(user=user)
            
            assignment = DeliveryAssignment.objects.get(
                id=assignment_id,
                delivery_person=delivery_person
            )
            
            # Get restaurant from order items
            order = assignment.order
            restaurant = None
            restaurant_location = None
            
            # Get restaurant from first order item
            if order.items.exists():
                first_item = order.items.first()
                if first_item.menu_item and first_item.menu_item.restaurant:
                    restaurant = first_item.menu_item.restaurant
                    if restaurant.latitude and restaurant.longitude:
                        restaurant_location = {
                            'latitude': float(restaurant.latitude),
                            'longitude': float(restaurant.longitude),
                            'name': restaurant.restaurant_name,
                            'address': restaurant.address,
                            'phone': restaurant.phone
                        }
            
            # Get delivery location from order
            delivery_location = None
            if order.delivery_latitude and order.delivery_longitude:
                delivery_location = {
                    'latitude': float(order.delivery_latitude),
                    'longitude': float(order.delivery_longitude),
                    'address': order.address,
                    'city': order.city,
                    'province': order.province
                }
            
            # Calculate distance if both locations available
            distance_km = None
            if restaurant_location and delivery_location:
                from math import radians, sin, cos, sqrt, atan2
                
                lat1 = radians(restaurant_location['latitude'])
                lon1 = radians(restaurant_location['longitude'])
                lat2 = radians(delivery_location['latitude'])
                lon2 = radians(delivery_location['longitude'])
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance_km = round(6371 * c, 2)
            
            # Get order items for delivery reference
            order_items = []
            for item in order.items.all():
                order_items.append({
                    'id': item.id,
                    'name': item.menu_item.name if item.menu_item else 'Unknown Item',
                    'quantity': item.quantity,
                    'price': str(item.price),
                    'total': str(item.get_total()),
                    'special_instructions': item.special_instructions or ''
                })
            
            # Prepare assignment data with map coordinates
            assignment_data = {
                'id': assignment.id,
                'order_number': assignment.order.order_number,
                'customer_name': assignment.order.full_name,
                'customer_phone': assignment.order.phone,
                'customer_email': assignment.order.email,
                'address': assignment.order.address,
                'city': assignment.order.city,
                'province': assignment.order.province,
                'postal_code': assignment.order.postal_code,
                'total': str(assignment.order.total),
                'subtotal': str(assignment.order.subtotal),
                'shipping_cost': str(assignment.order.shipping_cost),
                'tax_amount': str(assignment.order.tax_amount),
                'discount': str(assignment.order.discount),
                'payment_method': assignment.order.payment_method,
                'payment_status': assignment.order.payment_status,
                'status': assignment.status,
                'status_display': assignment.get_status_display(),
                'notes': assignment.notes or '',
                'failure_reason': assignment.failure_reason or '',
                'assigned_at': assignment.assigned_at.strftime('%Y-%m-%d %H:%M:%S') if assignment.assigned_at else None,
                'picked_up_at': assignment.picked_up_at.strftime('%Y-%m-%d %H:%M:%S') if assignment.picked_up_at else None,
                'in_transit_at': assignment.in_transit_at.strftime('%Y-%m-%d %H:%M:%S') if assignment.in_transit_at else None,
                'delivered_at': assignment.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if assignment.delivered_at else None,
                'created_at': assignment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': assignment.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                
                # Map locations
                'restaurant_location': restaurant_location,
                'delivery_location': delivery_location,
                
                # Distance information
                'distance_info': {
                    'km': distance_km,
                    'formatted': f"{distance_km:.2f} km" if distance_km else 'Not calculated',
                    'shipping_cost': str(assignment.order.shipping_cost),
                    'estimated_travel_time': f"{int(distance_km * 2)} minutes" if distance_km else 'Unknown'
                } if distance_km else None,
                
                # Order items
                'items': order_items,
                
                # Delivery actions based on status
                'available_actions': self.get_available_actions(assignment.status)
            }
            
            return Response({
                'success': True,
                'assignment': assignment_data
            }, status=200)
        
        except DeliveryPerson.DoesNotExist:
            return Response({
                'success': False, 
                'error': 'Delivery person not found',
                'error_code': 'DELIVERY_PERSON_NOT_FOUND'
            }, status=404)
        except DeliveryAssignment.DoesNotExist:
            return Response({
                'success': False, 
                'error': 'Assignment not found',
                'error_code': 'ASSIGNMENT_NOT_FOUND'
            }, status=404)
        except Exception as e:
            return Response({
                'success': False, 
                'error': str(e),
                'error_code': 'SERVER_ERROR'
            }, status=400)
    
    def get_available_actions(self, status):
        """Get available actions based on current assignment status"""
        actions = {
            'assigned': ['pick_up'],
            'picked_up': ['in_transit'],
            'in_transit': ['deliver', 'mark_failed'],
            'delivered': [],
            'failed': []
        }
        return actions.get(status, [])


# ============= Update Assignment Status =============
class UpdateAssignmentStatusApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request, assignment_id):
        try:
            user = request.user
            delivery_person = DeliveryPerson.objects.get(user=user)
            
            assignment = DeliveryAssignment.objects.get(
                id=assignment_id,
                delivery_person=delivery_person
            )
            
            new_status = request.data.get('status')
            notes = request.data.get('notes', '')
            
            # Validate status
            valid_statuses = ['assigned', 'picked_up', 'in_transit', 'delivered', 'failed']
            if new_status not in valid_statuses:
                return Response({
                    'success': False,
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }, status=400)
            
            # Update assignment
            assignment.status = new_status
            if notes:
                assignment.notes = notes
            
            # Update timestamps
            if new_status == 'picked_up' and not assignment.picked_up_at:
                assignment.picked_up_at = timezone.now()
            elif new_status == 'in_transit' and not assignment.in_transit_at:
                assignment.in_transit_at = timezone.now()
            elif new_status == 'delivered' and not assignment.delivered_at:
                assignment.delivered_at = timezone.now()
            
            assignment.save()
            
            return Response({
                'success': True,
                'message': f'Assignment status updated to {new_status}',
                'assignment': {
                    'id': assignment.id,
                    'status': assignment.status,
                    'updated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
                }
            }, status=200)
        
        except DeliveryPerson.DoesNotExist:
            return Response({'success': False, 'error': 'Delivery person not found'}, status=404)
        except DeliveryAssignment.DoesNotExist:
            return Response({'success': False, 'error': 'Assignment not found'}, status=404)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= Upload Delivery Photo =============
class UploadDeliveryPhotoApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request, assignment_id):
        try:
            user = request.user
            delivery_person = DeliveryPerson.objects.get(user=user)
            
            assignment = DeliveryAssignment.objects.get(
                id=assignment_id,
                delivery_person=delivery_person
            )
            
            if 'photo' not in request.FILES:
                return Response({'success': False, 'error': 'Photo file required'}, status=400)
            
            photo = request.FILES['photo']
            assignment.delivery_photo = photo
            assignment.save()
            
            return Response({
                'success': True,
                'message': 'Delivery photo uploaded successfully',
                'photo_url': assignment.delivery_photo.url
            }, status=200)
        
        except DeliveryPerson.DoesNotExist:
            return Response({'success': False, 'error': 'Delivery person not found'}, status=404)
        except DeliveryAssignment.DoesNotExist:
            return Response({'success': False, 'error': 'Assignment not found'}, status=404)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= Delivery Dashboard Stats =============
class DeliveryDashboardApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        try:
            user = request.user
            delivery_person = DeliveryPerson.objects.get(user=user)
            
            assignments = DeliveryAssignment.objects.filter(delivery_person=delivery_person)
            
            stats = {
                'total_assignments': assignments.count(),
                'assigned': assignments.filter(status='assigned').count(),
                'picked_up': assignments.filter(status='picked_up').count(),
                'in_transit': assignments.filter(status='in_transit').count(),
                'delivered': assignments.filter(status='delivered').count(),
                'failed': assignments.filter(status='failed').count(),
            }
            
            return Response({
                'success': True,
                'stats': stats
            }, status=200)
        
        except DeliveryPerson.DoesNotExist:
            return Response({'success': False, 'error': 'Delivery person not found'}, status=404)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)
        






# ================================================================
#     RESTAURANT & FOOD DELIVERY API 
# ================================================================

# ============= List All Restaurants =============
class RestaurantListApiView(APIView):
    """Get list of all active restaurants with basic info"""
    def get(self, request):
        try:
            city = request.GET.get('city', '').strip()
            cuisine = request.GET.get('cuisine', '').strip()
            search = request.GET.get('search', '').strip()
            
            restaurants = Restaurant.objects.filter(is_active=True, is_open=True)
            
            if city:
                restaurants = restaurants.filter(city__iexact=city)
            
            if search:
                restaurants = restaurants.filter(
                    restaurant_name__icontains=search
                ) | restaurants.filter(
                    description__icontains=search
                )
            
            if cuisine:
                restaurants = restaurants.filter(cuisines__icontains=cuisine)
            
            restaurants = restaurants.order_by('-rating', '-created_at')
            
            restaurant_data = []
            for restaurant in restaurants:
                restaurant_data.append({
                    'id': restaurant.id,
                    'slug': restaurant.slug,
                    'name': restaurant.restaurant_name,
                    'logo': restaurant.logo.url if restaurant.logo else None,
                    'banner': restaurant.banner.url if restaurant.banner else None,
                    'cuisines': restaurant.cuisines,
                    'city': restaurant.city,
                    'rating': float(restaurant.rating),
                    'avg_prep_time': restaurant.avg_prep_time,
                    'delivery_fee': float(restaurant.delivery_fee),
                    'min_order_value': float(restaurant.min_order_value),
                    'is_open': restaurant.is_open,
                    'menu_count': restaurant.menu_items.filter(is_available=True).count(),
                })
            
            return Response({'success': True, 'restaurants': restaurant_data}, status=200)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= Restaurant Details =============
class RestaurantDetailsApiView(APIView):
    """Get full restaurant details by ID or slug"""
    def get(self, request, restaurant_id):
        try:
            restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
            
            # Get all reviews
            reviews_count = restaurant.reviews.count()
            average_rating = restaurant.get_average_rating()
            
            # Get menu sections count
            sections_count = restaurant.menu_sections.filter(is_active=True).count()
            items_count = restaurant.menu_items.filter(is_available=True).count()
            
            restaurant_data = {
                'id': restaurant.id,
                'slug': restaurant.slug,
                'name': restaurant.restaurant_name,
                'logo': restaurant.logo.url if restaurant.logo else None,
                'banner': restaurant.banner.url if restaurant.banner else None,
                'description': clean_ckeditor_text(restaurant.description),
                'cuisines': restaurant.cuisines,
                'city': restaurant.city,
                'province': restaurant.get_province_display(),
                'phone': restaurant.phone,
                'address': restaurant.address,
                'rating': float(restaurant.rating),
                'average_rating': float(average_rating),
                'reviews_count': reviews_count,
                'avg_prep_time': restaurant.avg_prep_time,
                'delivery_fee': float(restaurant.delivery_fee),
                'min_order_value': float(restaurant.min_order_value),
                'is_open': restaurant.is_open,
                'menu_sections_count': sections_count,
                'menu_items_count': items_count,
                'created_at': restaurant.created_at.strftime('%Y-%m-%d %H:%M'),
            }
            
            return Response({'success': True, 'restaurant': restaurant_data}, status=200)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= Restaurant Menu Items (Grouped by Section) =============
class RestaurantMenuApiView(APIView):
    """Get all menu items for restaurant grouped by sections"""
    def get(self, request, restaurant_id):
        try:
            restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
            
            # Get all sections with their items
            sections = restaurant.menu_sections.filter(is_active=True).order_by('order')
            
            menu_data = []
            for section in sections:
                # Get items in this section
                items = section.menu_items.filter(is_available=True).order_by('-created_at')
                
                if items.exists():  # Only include sections with items
                    items_data = []
                    for item in items:
                        items_data.append({
                            'id': item.id,
                            'name': item.name,
                            'price': float(item.price),
                            'description': clean_ckeditor_text(item.description)[:100],  # Truncate
                            'image': item.image.url if item.image else None,
                            'is_vegetarian': item.is_vegetarian,
                            'prep_time': item.prep_time,
                            'is_available': item.is_available,
                            'average_rating': float(item.average_rating),
                            'reviews_count': item.reviews.count(),
                        })
                    
                    menu_data.append({
                        'section_id': section.id,
                        'section_name': section.name,
                        'section_description': section.description,
                        'items': items_data,
                    })
            
            return Response({
                'success': True,
                'restaurant_id': restaurant.id,
                'restaurant_name': restaurant.restaurant_name,
                'menu': menu_data
            }, status=200)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= Menu Item Details =============
class MenuItemDetailsApiView(APIView):
    """Get full details of a single menu item"""
    def get(self, request, menu_item_id):
        try:
            menu_item = get_object_or_404(MenuItem, id=menu_item_id, is_available=True)
            
            # Get all images
            images = [img.image.url for img in menu_item.images.all().order_by('order')]
            
            # Get dietary tags
            # tags = [tag.name for tag in menu_item.dietary_tags.all()]
            
            # Get reviews
            reviews_data = []
            for review in menu_item.reviews.all().order_by('-created_at')[:5]:  # Last 5 reviews
                reviews_data.append({
                    'user': f"{review.user.first_name} {review.user.last_name}",
                    'rating': review.rating,
                    'comment': review.comment,
                    'created_at': review.created_at.strftime('%Y-%m-%d %H:%M'),
                })
            
            menu_item_data = {
                'id': menu_item.id,
                'name': menu_item.name,
                'slug': menu_item.slug,
                'price': float(menu_item.price),
                'cost_price': float(menu_item.cost_price) if menu_item.cost_price else None,
                'description': clean_ckeditor_text(menu_item.description),
                'section_id': menu_item.section.id if menu_item.section else None,
                'section_name': menu_item.section.name if menu_item.section else None,
                'image': menu_item.image.url if menu_item.image else None,
                'gallery_images': images,
                'is_vegetarian': menu_item.is_vegetarian,
                'prep_time': menu_item.prep_time,
                # 'dietary_tags': tags,
                'is_available': menu_item.is_available,
                'average_rating': float(menu_item.average_rating),
                'reviews_count': menu_item.reviews.count(),
                'recent_reviews': reviews_data,
                'restaurant_id': menu_item.restaurant.id,
                'restaurant_name': menu_item.restaurant.restaurant_name,
                'created_at': menu_item.created_at.strftime('%Y-%m-%d %H:%M'),
            }
            
            return Response({'success': True, 'menu_item': menu_item_data}, status=200)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)


# ============= Add Menu Item to Food Cart =============
class AddMenuItemToCartApiView(APIView):
    """Add a menu item to user's food cart"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user = request.user
            menu_item_id = request.data.get('menu_item_id')
            quantity = int(request.data.get('quantity', 1))
            
            if not menu_item_id or quantity < 1:
                return Response({
                    'success': False,
                    'error': 'Invalid menu_item_id or quantity'
                }, status=400)
            
            menu_item = get_object_or_404(MenuItem, id=menu_item_id, is_available=True)
            
            # Check if item already in cart
            cart_item = Cart.objects.filter(user=user, menu_item=menu_item).first()
            
            if cart_item:
                # Update quantity
                cart_item.quantity += quantity
                cart_item.save()
            else:
                # Create new cart item
                cart_item = Cart.objects.create(
                    user=user,
                    menu_item=menu_item,
                    quantity=quantity
                )
            
            # Get updated cart summary
            cart_items = Cart.objects.filter(user=user)
            total_items = cart_items.count()
            total_quantity = sum(item.quantity for item in cart_items)
            
            return Response({
                'success': True,
                'message': f'{menu_item.name} added to cart',
                'menu_item': {
                    'id': menu_item.id,
                    'name': menu_item.name,
                    'price': float(menu_item.price),
                    'quantity': cart_item.quantity,
                    'subtotal': float(menu_item.price * cart_item.quantity),
                },
                'cart_summary': {
                    'total_items': total_items,
                    'total_quantity': total_quantity,
                }
            }, status=201)
        
        except MenuItem.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Menu item not found or not available'
            }, status=404)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)









# ============= Login via E-commerce Token =============
import jwt
from django.contrib.auth import login
@csrf_exempt
@api_view(['POST'])
def login_via_ecommerce_token(request):
    
    """
    Auto-login user from E-commerce JWT token.
    Expects: { "token": "<jwt>" }
    """
    token = request.data.get('token')
    if not token:
        return Response({'success': False, 'error': 'Token required'}, status=400)
    # import ipdb; ipdb.set_trace()

    try:
        # import ipdb; ipdb.set_trace()
        # Decode JWT without verifying signature (for cross-domain SSO)
        decoded = jwt.decode(token, options={"verify_signature": False})

        # Extract user info from token
        user_id = decoded.get('user_id')
        email = decoded.get('email')
        first_name = decoded.get('first_name', '')
        last_name = decoded.get('last_name', '')
        if "email" in decoded:
            email = decoded.get("email")
        else:
            email = request.data.get("email", None)
        if not user_id or not email:
            return Response({'success': False, 'error': 'Email or user_id missing in token'}, status=400)

        # Get or create user by user_id or email
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True
            }
        )

        # import ipdb;ipdb.set_trace()

        # If user was just created, set up profile and role
        if created:
            UserProfile.objects.create(user=user)
            UserRole.objects.create(user=user, role='customer')

        refresh = RefreshToken.for_user(user)


        


        return Response({
            'success': True,
            'user_id': user.id,
            'created': created,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'refresh': str(refresh),      
            'food_access': str(refresh.access_token),
            'ecommerce_access': token
        
        })

    except Exception as e:
        return Response({'success': False, 'error': f'Error: {str(e)}'}, status=400)
    

# My API View
from rest_framework import generics
from .serializers import (
    RestaurantSerializer,
    RestaurantsMenuSectionSerializer,
    RestaurantsMenuItemSerializer,
)
from rest_framework.permissions import AllowAny
# ================================================================
# Restaurant Detail API View
# ================================================================
class RestaurantsView(generics.ListAPIView):
    """Get the restaurants for customer 
    """
    queryset = Restaurant.objects.filter(is_active=True, verification_status='verified')
    serializer_class = RestaurantSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True, 
            'count': queryset.count(),
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
class RestaurantDetailView(generics.RetrieveAPIView):
    """Get the restaurant details by slug"""
    queryset = Restaurant.objects.filter(is_active=True, verification_status='verified')
    serializer_class = RestaurantSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True, 
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
# ================================================================
# Restaurant Menu Sections
# ================================================================

class RestaurantMenuSectionsView(generics.ListAPIView):
    """Get all menu sections with their items for a specific restaurant"""
    serializer_class = RestaurantsMenuSectionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        
        return MenuSection.objects.filter(
            restaurant=restaurant, 
            is_active=True
        ).order_by('order', 'id')

class RestaurantsMenuSectionsView(generics.ListAPIView):
    """Get all menu sections for all active restaurants with their items"""
    serializer_class = RestaurantsMenuSectionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return MenuSection.objects.filter(
            restaurant__is_active=True,
            restaurant__verification_status='verified',
            is_active=True
        ).select_related('restaurant').order_by('restaurant__restaurant_name', 'order', 'id')

    def list(self, request, *args, **kwargs):
        sections = self.get_queryset()
        
        # Group by restaurant
        restaurants = {}
        for section in sections:
            rest = section.restaurant
            
            if rest.id not in restaurants:
                restaurants[rest.id] = {
                    'restaurant_id': rest.id,
                    'restaurant_name': rest.restaurant_name,
                    'restaurant_slug': rest.slug,
                    'restaurant_logo': request.build_absolute_uri(rest.logo.url) if rest.logo else None,
                    'restaurant_banner': request.build_absolute_uri(rest.banner.url) if rest.banner else None,
                    'is_open': rest.is_open,
                    'rating': rest.get_average_rating(),
                    'reviews_count': rest.reviews.count(),
                    'cuisines': rest.cuisines,
                    'delivery_fee': float(rest.delivery_fee),
                    'min_order_value': float(rest.min_order_value),
                    'sections': []
                }
            
            # Add section with its items using your serializer
            restaurants[rest.id]['sections'].append(self.get_serializer(section).data)
        
        # Convert to list and add totals
        data = list(restaurants.values())
        for rest in data:
            rest['total_sections'] = len(rest['sections'])
            rest['total_menu_items'] = sum(s['items_count'] for s in rest['sections'])
        
        return Response({
            'success': True,
            'total_restaurants': len(data),
            'total_sections': sections.count(),
            'total_menu_items': sum(rest['total_menu_items'] for rest in data),
            'data': data
        })

    
class RestaurantMenuItem(generics.ListAPIView):
    """Get all menu items for a specific restaurant"""
    serializer_class = RestaurantsMenuItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        restaurant = get_object_or_404(Restaurant, slug=self.kwargs.get('restaurant_slug'))
        return MenuItem.objects.filter(restaurant=restaurant, is_available=True).order_by('id')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        restaurant = get_object_or_404(Restaurant, slug=self.kwargs.get('restaurant_slug'))
        
        return Response({
            'success': True,
            'restaurant': {
                'id': restaurant.id,
                'name': restaurant.restaurant_name,
                'slug': restaurant.slug,
                'logo': request.build_absolute_uri(restaurant.logo.url) if restaurant.logo else None,
                'banner': request.build_absolute_uri(restaurant.banner.url) if restaurant.banner else None,
                'is_open': restaurant.is_open,
                'rating': restaurant.get_average_rating(),
                'reviews_count': restaurant.reviews.count(),
            },
            'count': queryset.count(),
            'data': self.get_serializer(queryset, many=True).data
        })


class RestaurantsMenuItemsView(generics.ListAPIView):
    """Get all menu items from all restaurants"""
    serializer_class = RestaurantsMenuItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return MenuItem.objects.filter(
            is_available=True,
            restaurant__is_active=True,
            restaurant__verification_status='verified'
        ).select_related('restaurant').order_by('id')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        data = []
        for item, serialized_item in zip(queryset, serializer.data):
            data.append({
                'restaurant': {
                    'id': item.restaurant.id,
                    'name': item.restaurant.restaurant_name,
                    'slug': item.restaurant.slug,
                    'logo': request.build_absolute_uri(item.restaurant.logo.url) if item.restaurant.logo else None,
                    'is_open': item.restaurant.is_open,
                    'rating': item.restaurant.get_average_rating(),
                },
                **serialized_item  # This spreads the menu item data after restaurant
            })
        
        return Response({
            'success': True,
            'count': len(data),
            'data': data
        })

# Home Page API View
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.db import models
from dashboard.models import Restaurant, AdBanner, MenuSection, MenuItem, Address
from .serializers import (
    MenuSectionSerializer, 
    AdBannerSerializer, 
    MenuItemSerializer, 
    RestaurantSerializer,
    RestaurantMenuSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    OrderSerializer, 
    OrderListSerializer, 
    CreateOrderSerializer,
    AddressSerializer,
    CreateAddressSerializer,
)

class HomePage_APIView(APIView):
    """
    API endpoint for home page data
    GET /home/
    """
    
    def get(self, request, *args, **kwargs):
        # Get the first restaurant
        restaurant = Restaurant.objects.first()
        
        if not restaurant:
            return Response(
                {"error": "No restaurant found"},
                status=404
            )
        
        now = timezone.now()
        
        # Get active ad banners (valid for this restaurant or global)
        ad_banners = AdBanner.objects.filter(
            is_active=True,
            start_date__lte=now
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        ).filter(
            models.Q(restaurant=restaurant) | models.Q(restaurant__isnull=True)
        ).order_by('order')
        
        # Get active menu sections with their items
        explore_menu_sections = MenuSection.objects.filter(
            restaurant=restaurant,
            is_active=True
        ).prefetch_related('menu_items').order_by('order')
        
        # Get favorite/featured menu items
        favorite_menu_items = MenuItem.objects.filter(
            restaurant=restaurant,
            is_favorite=True
        ).order_by('-views_count', '-created_at')[:12]
        
        # Prepare response data
        response_data = {
            'restaurant': RestaurantSerializer(restaurant, context={'request': request}).data,
            'explore_menu_sections': MenuSectionSerializer(explore_menu_sections, many=True, context={'request': request}).data,
            'ad_banners': AdBannerSerializer(ad_banners, many=True, context={'request': request}).data,
            'favorite_menu_items': MenuItemSerializer(favorite_menu_items, many=True, context={'request': request}).data,
        }
        
        return Response(response_data, status=200)
    
# Explore Menu Page API View
from django.db.models import Prefetch

class RestaurantMenuAPIView(APIView):
    """
    API endpoint for restaurant menu
    GET /api/menus/
    """
    
    def get(self, request, *args, **kwargs):
        # Get the first restaurant
        restaurant = Restaurant.objects.first()
        
        if not restaurant:
            return Response(
                {
                    "success": False,
                    "message": "No restaurant found",
                    "data": None
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Optimize queries with prefetch_related
        # Remove 'order' from MenuItem ordering since it doesn't exist
        restaurant = Restaurant.objects.prefetch_related(
            Prefetch(
                'menu_sections',
                queryset=MenuSection.objects.filter(is_active=True).order_by('order'),
                to_attr='cached_sections'
            ),
            Prefetch(
                'menu_sections__menu_items',
                queryset=MenuItem.objects.filter(is_available=True).order_by('-is_featured', '-created_at'),
                to_attr='cached_items'
            ),
            'menu_sections__menu_items__reviews'
        ).first()
        
        # Serialize the data
        serializer = RestaurantMenuSerializer(restaurant, context={'request': request})
        
        return Response(
            {
                "success": True,
                "message": "Menu retrieved successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        
# ================================================================
# CART API VIEWS
# ================================================================
import uuid
class AddToCartView(APIView):
    """Add item to cart for Flutter app (supports both authenticated and guest users)"""
    permission_classes = [AllowAny]
    
    def get_authenticated_user(self, request):
        """Try to authenticate user from JWT token"""
        try:
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception as e:
            pass
        
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_or_create_guest_id(self, request):
        """Get existing guest_id from headers OR generate new one"""
        # First try to get from headers
        guest_id = request.headers.get('X-Guest-ID')
        
        if not guest_id:
            guest_id = request.data.get('guest_id')
        
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        # If no guest_id provided, generate a new one on the backend
        if not guest_id:
            guest_id = str(uuid.uuid4())
            print(f"Backend generated new guest_id: {guest_id}")
        else:
            print(f"📌 Using existing guest_id: {guest_id}")
        
        return guest_id
    
    def post(self, request):
        # First try to get authenticated user
        user = self.get_authenticated_user(request)
        
        serializer = AddToCartSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=400)
        
        data = serializer.validated_data
        menu_item_id = data['menu_item_id']
        quantity = data['quantity']
        
        # Handle authenticated user
        if user and user.is_authenticated:
            guest_id = None
            print(f"Authenticated user: {user.email or user.username}")
            
            # Get or create cart item for authenticated user
            cart_item, created = Cart.objects.get_or_create(
                user=user,
                menu_item_id=menu_item_id,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            cart_count = Cart.get_cart_count(user=user, guest_id=None)
            
            return Response({
                'success': True,
                'message': f'Added {quantity}x to cart',
                'cart_count': cart_count,
                'cart_item': CartItemSerializer(cart_item, context={'request': request}).data
            }, status=200)
        
        # Handle GUEST user - backend generates or retrieves guest_id
        guest_id = self.get_or_create_guest_id(request)
        
        # Validate menu item
        try:
            menu_item = MenuItem.objects.get(
                id=menu_item_id, 
                is_available=True,
                restaurant__is_active=True
            )
        except MenuItem.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Menu item not available'
            }, status=404)
        
        # Get or create cart item for guest
        cart_item, created = Cart.objects.get_or_create(
            guest_id=guest_id,
            menu_item=menu_item,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        cart_count = Cart.get_cart_count(user=None, guest_id=guest_id)
        
        # IMPORTANT: Return the guest_id to the client for storage
        return Response({
            'success': True,
            'message': f'Added {quantity}x {menu_item.name} to cart',
            'cart_count': cart_count,
            'guest_id': guest_id,  # Send back for client to store
            'is_new_guest': request.headers.get('X-Guest-ID') is None,  # Indicates if newly created
            'cart_item': CartItemSerializer(cart_item, context={'request': request}).data
        }, status=200)


class ViewCartView(APIView):
    """View current user's cart for Flutter app"""
    permission_classes = [AllowAny]
    
    def get_authenticated_user(self, request):
        """Try to authenticate user from JWT token - SAME as AddToCartView"""
        try:
            # Try JWT authentication
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception as e:
            # JWT authentication failed, but that's ok for guest users
            pass
        
        # Check if already authenticated through session
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_guest_id(self, request):
        """Get guest_id from request headers (Flutter sends this)"""
        # Get guest_id from headers (recommended for Flutter)
        guest_id = request.headers.get('X-Guest-ID')
        
        # Fallback to query parameter
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        # Fallback to request body (if POST/PUT)
        if not guest_id and request.method != 'GET':
            guest_id = request.data.get('guest_id')
        
        return guest_id
    
    def get(self, request):
        # Use SAME authentication method as AddToCartView
        user = self.get_authenticated_user(request)
        
        # Log for debugging
        print(f"ViewCart - Authentication result - User: {user}, Is Authenticated: {user.is_authenticated if user else False}")
        print(f"ViewCart - Authorization header: {request.headers.get('Authorization')}")
        
        # Case 1: User is authenticated (same logic as AddToCartView)
        if user and user.is_authenticated:
            print(f"ViewCart - Authenticated user: {user.email or user.username}")
            cart_items = Cart.get_cart_for_user(user=user, guest_id=None)
            is_guest = False
            
        # Case 2: Guest user
        else:
            print(f"ViewCart - Guest user")
            guest_id = self.get_guest_id(request)
            print(f"ViewCart - Guest ID: {guest_id}")
            
            # If no guest_id, return empty cart
            if not guest_id:
                return Response({
                    'success': True,
                    'data': {
                        'items': [],
                        'subtotal': 0,
                        'formatted_subtotal': "Rs. 0.00",
                        'total_items': 0,
                        'total_quantity': 0,
                        'is_guest': True
                    }
                })
            
            cart_items = Cart.get_cart_for_user(user=None, guest_id=guest_id)
            is_guest = True
        
        # Fetch cart items with related data
        cart_items = cart_items.select_related('menu_item', 'menu_item__restaurant').prefetch_related('options')
        
        print(f"ViewCart - Found {cart_items.count()} items in cart")
        
        # Calculate totals
        subtotal = Decimal('0.00')
        total_quantity = 0
        items_data = []
        
        for item in cart_items:
            item_total = item.total_price
            subtotal += item_total
            total_quantity += item.quantity
            items_data.append(CartItemSerializer(item, context={'request': request}).data)
        
        return Response({
            'success': True,
            'data': {
                'items': items_data,
                'subtotal': float(subtotal),
                'formatted_subtotal': f"Rs. {subtotal:,.2f}",
                'total_items': cart_items.count(),
                'total_quantity': total_quantity,
                'is_guest': is_guest
            }
        })


class UpdateCartItemView(APIView):
    """Update cart item quantity for Flutter app"""
    permission_classes = [AllowAny]
    
    def get_authenticated_user(self, request):
        """Try to authenticate user from JWT token - SAME as AddToCartView"""
        try:
            # Try JWT authentication
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception as e:
            # JWT authentication failed, but that's ok for guest users
            pass
        
        # Check if already authenticated through session
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_guest_id(self, request):
        """Get guest_id from request headers or query params"""
        # Only get guest_id if user is NOT authenticated
        guest_id = request.headers.get('X-Guest-ID')
        
        # Fallback to query parameter
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        # Fallback to request body
        if not guest_id:
            guest_id = request.data.get('guest_id')
        
        return guest_id
    
    def patch(self, request, cart_item_id):
        # First try to get authenticated user (SAME as AddToCartView)
        user = self.get_authenticated_user(request)
        
        # Log for debugging
        print(f"UpdateCartItem - Authentication result - User: {user}, Is Authenticated: {user.is_authenticated if user else False}")
        
        quantity = request.data.get('quantity')
        
        if not quantity or quantity < 1:
            return Response({
                'success': False,
                'message': 'Quantity must be at least 1'
            }, status=400)
        
        # Case 1: Authenticated user (SAME logic as AddToCartView)
        if user and user.is_authenticated:
            print(f"UpdateCartItem - Authenticated user: {user.email or user.username}")
            guest_id = None
            
        # Case 2: Guest user
        else:
            print(f"UpdateCartItem - Guest user")
            guest_id = self.get_guest_id(request)
            print(f"UpdateCartItem - Guest ID: {guest_id}")
            
            if not guest_id:
                return Response({
                    'success': False,
                    'message': 'guest_id is required. Please provide X-Guest-ID header'
                }, status=400)
        
        try:
            # Use the model's helper method to get cart items
            cart_items = Cart.get_cart_for_user(user=user if (user and user.is_authenticated) else None, 
                                                guest_id=guest_id if not (user and user.is_authenticated) else None)
            cart_item = cart_items.get(id=cart_item_id)
            
            # Update quantity
            cart_item.quantity = quantity
            cart_item.save()
            
            return Response({
                'success': True,
                'message': 'Cart updated successfully',
                'cart_item': CartItemSerializer(cart_item, context={'request': request}).data
            })
            
        except Cart.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Cart item not found'
            }, status=404)


class RemoveFromCartView(APIView):
    """Remove item from cart for Flutter app"""
    permission_classes = [AllowAny]
    
    def get_authenticated_user(self, request):
        """Try to authenticate user from JWT token"""
        try:
            # Try JWT authentication
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception as e:
            # JWT authentication failed, but that's ok for guest users
            pass
        
        # Check if already authenticated through session
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_guest_id(self, request):
        """Get guest_id from request headers (Flutter sends this)"""
        # Try headers first (recommended for mobile apps)
        guest_id = request.headers.get('X-Guest-ID')
        
        # Fallback to query parameter
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        # Fallback to request body
        if not guest_id:
            guest_id = request.data.get('guest_id')
        
        return guest_id
    
    def delete(self, request, cart_item_id):
        # First try to get authenticated user (SAME as AddToCartView)
        user = self.get_authenticated_user(request)
        
        # Log for debugging
        print(f"RemoveFromCart - Authentication result - User: {user}, Is Authenticated: {user.is_authenticated if user else False}")
        
        # Case 1: Authenticated user (SAME logic as other views)
        if user and user.is_authenticated:
            print(f"RemoveFromCart - Authenticated user: {user.email or user.username}")
            guest_id = None
            
        # Case 2: Guest user
        else:
            print(f"RemoveFromCart - Guest user")
            guest_id = self.get_guest_id(request)
            print(f"RemoveFromCart - Guest ID: {guest_id}")
            
            if not guest_id:
                return Response({
                    'success': False,
                    'message': 'guest_id is required for guest users. Please provide X-Guest-ID header'
                }, status=400)
        
        try:
            # Get cart item with proper ownership verification
            if user and user.is_authenticated:
                cart_item = Cart.objects.get(id=cart_item_id, user=user)
            else:
                cart_item = Cart.objects.get(id=cart_item_id, guest_id=guest_id, user__isnull=True)
            
            cart_item.delete()
            
            # Get updated cart count using your helper method
            if user and user.is_authenticated:
                cart_items = Cart.get_cart_for_user(user=user, guest_id=None)
            else:
                cart_items = Cart.get_cart_for_user(user=None, guest_id=guest_id)
            
            cart_count = cart_items.count()
            
            return Response({
                'success': True,
                'message': 'Item removed from cart',
                'cart_count': cart_count
            })
            
        except Cart.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Cart item not found'
            }, status=404)


class ClearCartView(APIView):
    """Clear entire cart for Flutter app"""
    permission_classes = [AllowAny]
    
    def get_authenticated_user(self, request):
        """Try to authenticate user from JWT token - SAME as other views"""
        try:
            # Try JWT authentication
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception as e:
            # JWT authentication failed, but that's ok for guest users
            pass
        
        # Check if already authenticated through session
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_guest_id(self, request):
        """Get guest_id from request headers (sent by Flutter)"""
        # Get guest_id from headers (recommended for Flutter)
        guest_id = request.headers.get('X-Guest-ID')
        
        # Fallback to query parameter
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        # Fallback to request body
        if not guest_id:
            guest_id = request.data.get('guest_id')
        
        return guest_id
    
    def delete(self, request):
        # First try to get authenticated user (SAME as other views)
        user = self.get_authenticated_user(request)
        
        # Log for debugging
        print(f"ClearCart - Authentication result - User: {user}, Is Authenticated: {user.is_authenticated if user else False}")
        
        # Case 1: Authenticated user (SAME logic as other views)
        if user and user.is_authenticated:
            print(f"ClearCart - Authenticated user: {user.email or user.username}")
            # Authenticated user - clear their cart
            deleted_count, _ = Cart.objects.filter(user=user).delete()
            message = f'Cleared {deleted_count} items from your cart'
            
        # Case 2: Guest user
        else:
            print(f"ClearCart - Guest user")
            guest_id = self.get_guest_id(request)
            print(f"ClearCart - Guest ID: {guest_id}")
            
            if not guest_id:
                return Response({
                    'success': False,
                    'message': 'guest_id is required for guest users. Please provide X-Guest-ID header'
                }, status=400)
            
            # Clear guest cart using guest_id
            deleted_count, _ = Cart.objects.filter(
                guest_id=guest_id, 
                user__isnull=True
            ).delete()
            message = f'Cleared {deleted_count} items from guest cart'
        
        return Response({
            'success': True,
            'message': message,
            'deleted_count': deleted_count
        })


class MergeGuestCartView(APIView):
    """
    Merge guest cart into user cart after login/signup
    For Flutter app: Send guest_id in headers
    
    Headers:
        Authorization: Bearer <jwt_token>  (after login)
        X-Guest-ID: <uuid_from_flutter>    (guest cart identifier)
    """
    permission_classes = [AllowAny]  # Changed to AllowAny, we'll authenticate manually
    
    def get_authenticated_user(self, request):
        """Try to authenticate user from JWT token - SAME as other views"""
        try:
            # Try JWT authentication
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception as e:
            # JWT authentication failed
            print(f"MergeGuestCart - JWT auth error: {e}")
            pass
        
        # Check if already authenticated through session
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_guest_id(self, request):
        """Get guest_id from request headers (sent by Flutter app)"""
        # Try headers first (recommended for Flutter)
        guest_id = request.headers.get('X-Guest-ID')
        
        # Fallback to query parameter
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        # Fallback to request body
        if not guest_id:
            guest_id = request.data.get('guest_id')
        
        return guest_id
    
    def post(self, request):
        # First authenticate the user manually
        user = self.get_authenticated_user(request)
        
        # Debug logging
        print(f"MergeGuestCart - Authentication result - User: {user}, Is Authenticated: {user.is_authenticated if user else False}")
        print(f"MergeGuestCart - Authorization header: {request.headers.get('Authorization')}")
        
        # Check if user is authenticated
        if not user or not user.is_authenticated:
            return Response({
                'success': False,
                'message': 'Authentication required. Please provide valid JWT token',
                'error_code': 'UNAUTHORIZED'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get guest_id from request
        guest_id = self.get_guest_id(request)
        
        print(f"MergeGuestCart - Guest ID: {guest_id}")
        
        if not guest_id:
            return Response({
                'success': False,
                'message': 'guest_id is required. Please provide X-Guest-ID header',
                'error_code': 'MISSING_GUEST_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if there are any items in guest cart
        guest_items = Cart.objects.filter(guest_id=guest_id, user__isnull=True)
        
        print(f"MergeGuestCart - Found {guest_items.count()} items in guest cart")
        
        if not guest_items.exists():
            return Response({
                'success': True,
                'message': 'No guest cart items to merge',
                'merged_count': 0,
                'updated_count': 0,
                'cart_count': Cart.objects.filter(user=user).count()
            }, status=status.HTTP_200_OK)
        
        # Store counts before merge
        guest_count = guest_items.count()
        user_items_before = Cart.objects.filter(user=user).count()
        
        print(f"MergeGuestCart - Guest count: {guest_count}, User items before: {user_items_before}")
        
        # Merge guest cart into user cart
        try:
            # Check if the merge method exists
            if hasattr(Cart, 'merge_guest_cart'):
                merged_cart = Cart.merge_guest_cart(user, guest_id)
                final_cart_count = merged_cart.count()
            else:
                # Manual merge if method doesn't exist
                for guest_item in guest_items:
                    # Check if user already has this menu item
                    existing_item = Cart.objects.filter(
                        user=user,
                        menu_item=guest_item.menu_item
                    ).first()
                    
                    if existing_item:
                        # Update quantity
                        existing_item.quantity += guest_item.quantity
                        existing_item.save()
                    else:
                        # Create new cart item for user
                        Cart.objects.create(
                            user=user,
                            menu_item=guest_item.menu_item,
                            quantity=guest_item.quantity
                        )
                
                # Clear guest cart
                guest_items.delete()
                final_cart_count = Cart.objects.filter(user=user).count()
            
            # Ensure guest cart is cleared
            Cart.objects.filter(guest_id=guest_id, user__isnull=True).delete()
            
            print(f"MergeGuestCart - Final cart count: {final_cart_count}")
            
            return Response({
                'success': True,
                'message': f'Successfully merged {guest_count} item(s) from guest cart',
                'merged_count': guest_count,
                'user_items_before': user_items_before,
                'cart_count': final_cart_count,
                'total_items': final_cart_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"MergeGuestCart - Error: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error merging cart: {str(e)}',
                'error_code': 'MERGE_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# ================================================================
#  End of CART API VIEWS    
# ================================================================

# ================================================================
# Order API Views
# ================================================================
class GetUserProfileView(APIView):
    """
    Get logged-in user's profile information
    Requires JWT authentication
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        profile = getattr(user, 'profile', None)
        
        # Create full name
        full_name = ""
        if user.first_name or user.last_name:
            full_name = f"{user.first_name} {user.last_name}".strip()
        else:
            full_name = user.username
        
        return Response({
            'success': True,
            'data': {
                'full_name': full_name,
                'email': user.email,
                'phone': profile.phone if profile else '',
                'gender': profile.gender if profile else '',
                'avatar': profile.avatar.url if profile and profile.avatar else None,
                'address': profile.address if profile else '',
                'city': profile.city if profile else '',
                'province': profile.province if profile else '',
            }
        })
    
from math import radians, sin, cos, sqrt, atan2
import requests

class CalculateDeliveryAPIView(APIView):
    """
    API to calculate delivery distance and shipping cost in real-time
    POST /api/calculate-delivery/
    
    Request Body:
    {
        "delivery_latitude": 27.7172453,
        "delivery_longitude": 85.3239605,
        "restaurant_id": 1 (optional - if not provided, will get from cart)
    }
    
    Response:
    {
        "success": true,
        "data": {
            "distance": {...},
            "shipping_cost": {...},
            "delivery_info": {...},
            "restaurant": {...},
            "delivery_location": {...}
        }
    }
    """
    permission_classes = [AllowAny]
    
    def get_authenticated_user(self, request):
        """Get authenticated user from JWT token"""
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception:
            pass
        
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_guest_id(self, request):
        """Get guest_id from headers"""
        guest_id = request.headers.get('X-Guest-ID')
        if not guest_id:
            guest_id = request.data.get('guest_id')
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        return guest_id
    
    def get_restaurant_from_cart(self, request):
        """Get restaurant from user's cart"""
        user = self.get_authenticated_user(request)
        cart_items = None
        
        if user and user.is_authenticated:
            cart_items = Cart.objects.filter(user=user)
        else:
            guest_id = self.get_guest_id(request)
            if guest_id:
                cart_items = Cart.objects.filter(guest_id=guest_id, user__isnull=True)
        
        if not cart_items or not cart_items.exists():
            return None
        
        # Get restaurant from first cart item
        first_item = cart_items.first()
        restaurant = first_item.menu_item.restaurant
        
        # Verify all items are from same restaurant
        for item in cart_items:
            if item.menu_item.restaurant != restaurant:
                return None
        
        return restaurant
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        # Convert to radians
        lat1, lon1 = radians(float(lat1)), radians(float(lon1))
        lat2, lon2 = radians(float(lat2)), radians(float(lon2))
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = 6371 * c  # Earth's radius in kilometers
        
        return round(distance, 2)
    
    def calculate_shipping_cost(self, distance_km):
        """
        Calculate shipping cost based on distance
        Free delivery within 5km, NPR 100 beyond 5km
        """
        if distance_km <= 5:
            return Decimal('0.00')
        else:
            return Decimal('100.00')
    
    def calculate_estimated_time(self, distance_km):
        """Calculate estimated delivery time in minutes"""
        # Base time: 30 minutes for preparation + 2 minutes per km for delivery
        base_time = 30
        delivery_time = int(distance_km * 2)
        total_time = base_time + delivery_time
        
        # Return range
        min_time = total_time
        max_time = total_time + 10
        
        return f"{min_time}-{max_time} minutes"
    
    def reverse_geocode(self, latitude, longitude, language='en'):
        """
        Convert coordinates to human-readable address using OpenStreetMap Nominatim API
        Returns address string in specified language
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            language: Language code (default 'en' for English, 'ne' for Nepali)
        """
        try:
            # Using OpenStreetMap Nominatim API (free, no API key required)
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'addressdetails': 1,
                'zoom': 18,
                'accept-language': language
            }
            
            headers = {
                'User-Agent': 'NFC-FoodDelivery/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract address components
                address = data.get('address', {})
                
                # Get all possible area-related fields
                suburb = address.get('suburb', '')
                neighbourhood = address.get('neighbourhood', '')
                city_district = address.get('city_district', '')
                district = address.get('state_district', '')
                county = address.get('county', '')
                municipality = address.get('municipality', '')
                town = address.get('town', '')
                village = address.get('village', '')
                hamlet = address.get('hamlet', '')
                
                # Priority order for area field (first non-empty value)
                area_options = [
                    neighbourhood,
                    suburb,
                    city_district,
                    municipality,
                    county,
                    district,
                    town,
                    village,
                    hamlet
                ]
                
                # Get the first non-empty area
                area = next((item for item in area_options if item), '')
                
                # Get city (fallback to town or village)
                city = address.get('city', '') or address.get('town', '') or address.get('village', '')
                
                # Get district/state
                state = address.get('state', '')
                
                # Get road
                road = address.get('road', '')
                
                # Get country
                country = address.get('country', '')
                
                # Get postal code
                postcode = address.get('postcode', '')
                
                # Create display name
                display_name = data.get('display_name', '')
                
                # Build a cleaner formatted address
                address_parts = []
                if road:
                    address_parts.append(road)
                if area:
                    address_parts.append(area)
                if city and city != area:
                    address_parts.append(city)
                if state:
                    address_parts.append(state)
                if country:
                    address_parts.append(country)
                
                # If no specific parts found, use display_name
                if not address_parts:
                    formatted_address = display_name
                else:
                    formatted_address = ', '.join(address_parts)
                
                # If address is still too long, truncate
                if len(formatted_address) > 150:
                    formatted_address = ', '.join(address_parts[:4])
                
                result = {
                    'full_address': formatted_address,
                    'road': road,
                    'area': area,
                    'city': city,
                    'district': district,
                    'state': state,
                    'country': country,
                    'postal_code': postcode,
                    'raw_display_name': display_name  # Keep original for debugging
                }
                
                return result
            else:
                return None
                
        except Exception as e:
            print(f"Reverse geocoding error: {e}")
            return None
    
    def validate_delivery_zone(self, restaurant, distance_km):
        """
        Validate if delivery is possible to the location
        Returns (is_valid, message)
        """
        # Maximum delivery distance (can be customized per restaurant)
        max_delivery_distance = getattr(restaurant, 'max_delivery_distance', 15)
        
        if distance_km > max_delivery_distance:
            return False, f"Delivery distance {distance_km:.2f} km exceeds maximum allowed distance of {max_delivery_distance} km"
        
        return True, "Delivery available"
    
    def post(self, request):
        # Get delivery coordinates from request
        delivery_latitude = request.data.get('delivery_latitude')
        delivery_longitude = request.data.get('delivery_longitude')
        restaurant_id = request.data.get('restaurant_id')
        language = request.data.get('language', 'en')  # Default to English
        
        # Validate delivery coordinates
        if not delivery_latitude or not delivery_longitude:
            return Response({
                'success': False,
                'message': 'Delivery latitude and longitude are required',
                'error_code': 'MISSING_COORDINATES'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate coordinate ranges
        try:
            del_lat = float(delivery_latitude)
            del_lng = float(delivery_longitude)
            
            if not (-90 <= del_lat <= 90):
                return Response({
                    'success': False,
                    'message': 'Invalid latitude. Must be between -90 and 90',
                    'error_code': 'INVALID_LATITUDE'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not (-180 <= del_lng <= 180):
                return Response({
                    'success': False,
                    'message': 'Invalid longitude. Must be between -180 and 180',
                    'error_code': 'INVALID_LONGITUDE'
                }, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid coordinate format. Please provide valid numbers',
                'error_code': 'INVALID_COORDINATE_FORMAT'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get restaurant
        restaurant = None
        
        # Method 1: Get by restaurant_id if provided
        if restaurant_id:
            try:
                restaurant = Restaurant.objects.get(id=restaurant_id)
            except Restaurant.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Restaurant not found',
                    'error_code': 'RESTAURANT_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Method 2: Get from user's cart
            restaurant = self.get_restaurant_from_cart(request)
            if not restaurant:
                return Response({
                    'success': False,
                    'message': 'Unable to determine restaurant. Your cart is empty or contains items from multiple restaurants. Please provide restaurant_id or add items to cart.',
                    'error_code': 'RESTAURANT_NOT_DETERMINED'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if restaurant has coordinates
        if not restaurant.latitude or not restaurant.longitude:
            return Response({
                'success': False,
                'message': f'Restaurant "{restaurant.restaurant_name}" does not have location coordinates set. Please contact support.',
                'error_code': 'RESTAURANT_NO_COORDINATES'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate distance and delivery info
        try:
            # Convert to float for calculation
            rest_lat = float(restaurant.latitude)
            rest_lng = float(restaurant.longitude)
            
            # Calculate distance
            distance_km = self.calculate_distance(rest_lat, rest_lng, del_lat, del_lng)
            
            # Calculate shipping cost
            shipping_cost = self.calculate_shipping_cost(distance_km)
            
            # Calculate estimated delivery time
            estimated_time = self.calculate_estimated_time(distance_km)
            
            # Validate delivery zone
            is_deliverable, delivery_message = self.validate_delivery_zone(restaurant, distance_km)
            
            # Reverse geocode delivery location to get address in English
            delivery_address = self.reverse_geocode(del_lat, del_lng, language)
            
            # Also reverse geocode restaurant location in English
            restaurant_address = self.reverse_geocode(rest_lat, rest_lng, language)
            
            # Prepare response
            response_data = {
                'success': True,
                'data': {
                    'distance': {
                        'km': distance_km,
                        'formatted_km': f"{distance_km:.2f} km",
                        'meters': int(distance_km * 1000),
                        'formatted_meters': f"{int(distance_km * 1000)} meters"
                    },
                    'shipping_cost': {
                        'amount': float(shipping_cost),
                        'formatted': f"Rs {shipping_cost:,.2f}",
                        'currency': 'NPR'
                    },
                    'delivery_info': {
                        'is_free_delivery': shipping_cost == 0,
                        'free_delivery_up_to_km': 5,
                        'additional_charge_for_excess': 'NPR 100',
                        'estimated_delivery_time': estimated_time,
                        'can_deliver': is_deliverable,
                        'message': delivery_message if not is_deliverable else (
                            'Free delivery within 5km' if distance_km <= 5 
                            else f'Delivery charge of Rs 100 applied for {distance_km:.2f} km distance'
                        ),
                        'warning': None if is_deliverable else 'Delivery beyond maximum radius is not available'
                    },
                    'restaurant': {
                        'id': restaurant.id,
                        'name': restaurant.restaurant_name,
                        'latitude': rest_lat,
                        'longitude': rest_lng,
                        'address': restaurant.address,
                        'city': restaurant.city,
                        'phone': restaurant.phone,
                        'full_address': restaurant_address['full_address'] if restaurant_address else restaurant.address,
                        'location_details': restaurant_address if restaurant_address else {
                            'full_address': restaurant.address,
                            'road': '',
                            'area': restaurant.city,
                            'city': restaurant.city,
                            'district': '',
                            'state': restaurant.province,
                            'country': 'Nepal',
                            'postal_code': ''
                        }
                    },
                    'delivery_location': {
                        'latitude': del_lat,
                        'longitude': del_lng,
                        'address': delivery_address['full_address'] if delivery_address else 'Address not found',
                        'details': {
                            'road': delivery_address['road'] if delivery_address else '',
                            'area': delivery_address['area'] if delivery_address else '',
                            'city': delivery_address['city'] if delivery_address else '',
                            'district': delivery_address['district'] if delivery_address else '',
                            'state': delivery_address['state'] if delivery_address else '',
                            'country': delivery_address['country'] if delivery_address else 'Nepal',
                            'postal_code': delivery_address['postal_code'] if delivery_address else ''
                        } if delivery_address else None
                    }
                }
            }
            
            # Add warning if distance is too far
            if not is_deliverable:
                response_data['data']['delivery_info']['message'] = f"Distance {distance_km:.2f} km exceeds maximum delivery radius. Please choose a closer location or contact restaurant directly."
            
            # Add nearby restaurants suggestion if delivery not available
            if not is_deliverable:
                nearby_restaurants = self.get_nearby_restaurants(del_lat, del_lng, restaurant.id)
                if nearby_restaurants:
                    response_data['data']['nearby_restaurants'] = nearby_restaurants
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'message': f'Error calculating delivery distance: {str(e)}',
                'error_code': 'CALCULATION_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_nearby_restaurants(self, latitude, longitude, exclude_restaurant_id):
        """
        Get nearby restaurants if delivery is not available
        """
        try:
            # Find restaurants within 5km of delivery location
            nearby_restaurants = Restaurant.objects.filter(
                is_active=True,
                latitude__isnull=False,
                longitude__isnull=False
            ).exclude(id=exclude_restaurant_id)[:10]
            
            suggestions = []
            for rest in nearby_restaurants:
                if rest.latitude and rest.longitude:
                    dist = self.calculate_distance(
                        float(rest.latitude),
                        float(rest.longitude),
                        latitude,
                        longitude
                    )
                    if dist <= 5:  # Within 5km of delivery location
                        suggestions.append({
                            'id': rest.id,
                            'name': rest.restaurant_name,
                            'distance_km': dist,
                            'formatted_distance': f"{dist:.2f} km",
                            'address': rest.address,
                            'city': rest.city,
                            'phone': rest.phone,
                            'estimated_delivery_time': self.calculate_estimated_time(dist)
                        })
            
            return suggestions[:3]  # Return top 3
        except Exception as e:
            print(f"Error finding nearby restaurants: {e}")
            return None
        
# Address Views
from django.db import IntegrityError
class AddressListCreateView(APIView):
    """List all addresses for authenticated user or create new address"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all addresses for the authenticated user"""
        addresses = request.user.addresses.all()
        serializer = AddressSerializer(addresses, many=True, context={'request': request})
        return Response({
            'success': True,
            'addresses': serializer.data,
            'total': addresses.count(),
            'default_address': AddressSerializer(
                request.user.addresses.filter(is_default=True).first(),
                context={'request': request}
            ).data if request.user.addresses.filter(is_default=True).exists() else None
        })
    
    def post(self, request):
        serializer = CreateAddressSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            try:
                address = serializer.save(user=request.user)
            except IntegrityError:
                return Response({
                    "success": False,
                    "message": "Address type already exists for this user."
                }, status=400)

            return Response({
                'success': True,
                'message': 'Address created successfully',
                'address': AddressSerializer(address, context={'request': request}).data
            }, status=201)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)

class AddressDetailView(APIView):
    """Get, update, or delete a specific address"""
    permission_classes = [IsAuthenticated]
    
    def get_address(self, request, address_id):
        """Helper to get address and check ownership"""
        try:
            address = request.user.addresses.get(id=address_id)
            return address
        except Address.DoesNotExist:
            return None
    
    def get(self, request, address_id):
        """Get address details"""
        address = self.get_address(request, address_id)
        if not address:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddressSerializer(address, context={'request': request})
        return Response({
            'success': True,
            'address': serializer.data
        })
    
    def put(self, request, address_id):
        """Update address - full update"""
        address = self.get_address(request, address_id)
        if not address:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Remove partial=True for full update
        serializer = CreateAddressSerializer(address, data=request.data, context={'request': request})
        
        if serializer.is_valid():
            updated_address = serializer.save()
            address_serializer = AddressSerializer(updated_address, context={'request': request})
            return Response({
                'success': True,
                'message': 'Address updated successfully',
                'address': address_serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Add this new method for partial updates
    def patch(self, request, address_id):
        """Partial update address"""
        address = self.get_address(request, address_id)
        if not address:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CreateAddressSerializer(address, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            updated_address = serializer.save()
            address_serializer = AddressSerializer(updated_address, context={'request': request})
            return Response({
                'success': True,
                'message': 'Address updated successfully',
                'address': address_serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, address_id):
        """Delete address"""
        address = self.get_address(request, address_id)
        if not address:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if this is the default address
        was_default = address.is_default
        
        address.delete()
        
        # If deleted address was default, set another address as default if available
        if was_default:
            next_address = request.user.addresses.first()
            if next_address:
                next_address.is_default = True
                next_address.save()
        
        return Response({
            'success': True,
            'message': 'Address deleted successfully'
        })

class SetDefaultAddressView(APIView):
    """Set an address as default for the user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, address_id):
        try:
            address = request.user.addresses.get(id=address_id)
            
            # Set this address as default (the save method will handle others)
            address.is_default = True
            address.save()
            
            serializer = AddressSerializer(address, context={'request': request})
            return Response({
                'success': True,
                'message': 'Default address updated successfully',
                'default_address': serializer.data
            })
        except Address.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)

class GetUserAddressesView(APIView):
    """Get user addresses with optional filtering by type"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        address_type = request.query_params.get('type')
        
        addresses = request.user.addresses.all()
        
        if address_type:
            addresses = addresses.filter(address_type=address_type)
        
        serializer = AddressSerializer(addresses, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'addresses': serializer.data,
            'filter': address_type if address_type else 'all',
            'count': addresses.count()
        })

class CreateOrderView(APIView):
    """
    Create a new order from cart items for Flutter app
    POST /api/orders/create/
    """
    permission_classes = [AllowAny]
    
    def get_authenticated_user(self, request):
        """Try to authenticate user from JWT token"""
        try:
            # Try JWT authentication
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception as e:
            # JWT authentication failed, but that's ok for guest users
            pass
        
        # Check if already authenticated through session
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_guest_id(self, request):
        """Get guest_id from request headers (Flutter sends this)"""
        # Get guest_id from headers (recommended)
        guest_id = request.headers.get('X-Guest-ID')
        
        # Fallback to request body
        if not guest_id:
            guest_id = request.data.get('guest_id')
        
        # Fallback to query parameter
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        return guest_id
    
    def get_cart_items(self, request, cart_item_ids=None, single_cart_item_id=None):
        """
        Get cart items for current user/guest
        Supports: entire cart, specific IDs, or single item
        """
        # First try to get authenticated user
        user = self.get_authenticated_user(request)
        
        if user and user.is_authenticated:
            print(f"Get cart for authenticated user: {user.email}")
            cart_items = Cart.get_cart_for_user(user=user)
        else:
            guest_id = self.get_guest_id(request)
            print(f"Get cart for guest user with ID: {guest_id}")
            if not guest_id:
                return Cart.objects.none()
            cart_items = Cart.get_cart_for_user(guest_id=guest_id)
        
        # Filter by single cart item ID (Buy Now)
        if single_cart_item_id:
            cart_items = cart_items.filter(id=single_cart_item_id)
            print(f"Filtered to single cart item: {single_cart_item_id}")
        
        # Filter by specific cart item IDs
        elif cart_item_ids:
            cart_items = cart_items.filter(id__in=cart_item_ids)
            print(f"Filtered to {cart_items.count()} specific cart items")
        
        return cart_items
    
    def validate_cart_items_ownership(self, request, cart_item_ids):
        """Validate that all cart item IDs belong to the current user/guest"""
        user = self.get_authenticated_user(request)
        
        if user and user.is_authenticated:
            valid_items = Cart.objects.filter(
                id__in=cart_item_ids, 
                user=user
            ).count()
        else:
            guest_id = self.get_guest_id(request)
            if not guest_id:
                return False, []
            
            valid_items = Cart.objects.filter(
                id__in=cart_item_ids,
                guest_id=guest_id,
                user__isnull=True
            ).count()
        
        all_valid = valid_items == len(cart_item_ids)
        
        valid_ids = set(Cart.objects.filter(
            id__in=cart_item_ids
        ).values_list('id', flat=True))
        invalid_ids = list(set(cart_item_ids) - valid_ids)
        
        return all_valid, invalid_ids
    
    def get_user_default_info(self, user):
        """Get default user information from profile"""
        profile_data = {
            'full_name': '',
            'phone': '',
            'email': '',
            'address': '',
            'city': '',
            'province': '',
            'postal_code': ''
        }
        
        if not user or not user.is_authenticated:
            return profile_data
        
        # Get user's full name
        profile_data['full_name'] = user.get_full_name()
        if not profile_data['full_name']:
            profile_data['full_name'] = f"{user.first_name} {user.last_name}".strip()
        if not profile_data['full_name']:
            profile_data['full_name'] = user.username
        
        # Get email
        profile_data['email'] = user.email or ''
        
        # Get profile info
        try:
            if hasattr(user, 'profile'):
                profile = user.profile
                profile_data['phone'] = profile.phone or ''
                profile_data['address'] = profile.address or ''
                profile_data['city'] = profile.city or ''
                profile_data['province'] = profile.province or ''
                # profile_data['postal_code'] = profile.postal_code or ''  # Uncomment if you have postal_code in UserProfile
        except:
            pass
        
        return profile_data
    
    def get_client_ip(self, request):
        """Get client IP address for tracking"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1 = radians(float(lat1)), radians(float(lon1))
        lat2, lon2 = radians(float(lat2)), radians(float(lon2))
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        return round(distance, 2)
    
    def get_restaurant_from_cart(self, cart_items):
        """Get the restaurant from cart items (all items should be from same restaurant)"""
        if not cart_items.exists():
            return None
        
        # Get restaurant from first cart item
        first_item = cart_items.first()
        restaurant = first_item.menu_item.restaurant
        
        # Verify all items are from same restaurant
        for item in cart_items:
            if item.menu_item.restaurant != restaurant:
                raise ValueError("All cart items must be from the same restaurant")
        
        return restaurant
    
    @transaction.atomic
    def post(self, request):
        # First try to get authenticated user
        user = self.get_authenticated_user(request)
        
        # Debug logging
        print(f"CreateOrder - User authenticated: {user.is_authenticated if user else False}")
        print(f"CreateOrder - User: {user.email if user else 'None'}")
        
        # Determine checkout type
        cart_item_ids = request.data.get('cart_item_ids', [])
        single_cart_item_id = request.data.get('cart_item_id')
        address_id = request.data.get('address_id')  # NEW: For selecting saved address
        
        # Validate: Can't have both cart_item_ids and cart_item_id
        if cart_item_ids and single_cart_item_id:
            return Response({
                'success': False,
                'message': 'Cannot specify both cart_item_ids and cart_item_id. Use one or the other.',
                'error_code': 'INVALID_REQUEST'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate single cart item ID if provided
        if single_cart_item_id:
            is_valid, invalid_ids = self.validate_cart_items_ownership(
                request, [single_cart_item_id]
            )
            
            if not is_valid:
                return Response({
                    'success': False,
                    'message': f'Cart item with ID {single_cart_item_id} not found',
                    'invalid_cart_item_id': single_cart_item_id,
                    'error_code': 'INVALID_CART_ITEM'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate multiple cart item IDs if provided
        elif cart_item_ids:
            is_valid, invalid_ids = self.validate_cart_items_ownership(request, cart_item_ids)
            
            if not is_valid:
                return Response({
                    'success': False,
                    'message': f'Invalid cart item IDs: {invalid_ids}',
                    'invalid_cart_item_ids': invalid_ids,
                    'error_code': 'INVALID_CART_ITEMS'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get cart items based on checkout type
        cart_items = self.get_cart_items(
            request, 
            cart_item_ids=cart_item_ids if cart_item_ids else None,
            single_cart_item_id=single_cart_item_id
        )
        
        if not cart_items.exists():
            if single_cart_item_id:
                return Response({
                    'success': False,
                    'message': f'Cart item with ID {single_cart_item_id} not found',
                    'error_code': 'CART_ITEM_NOT_FOUND'
                }, status=status.HTTP_400_BAD_REQUEST)
            elif cart_item_ids:
                return Response({
                    'success': False,
                    'message': 'No valid cart items found for the provided IDs',
                    'requested_ids': cart_item_ids,
                    'error_code': 'CART_ITEMS_NOT_FOUND'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'success': False,
                    'message': 'Your cart is empty',
                    'error_code': 'EMPTY_CART'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get restaurant from cart items
        try:
            restaurant = self.get_restaurant_from_cart(cart_items)
            if not restaurant:
                return Response({
                    'success': False,
                    'message': 'Unable to determine restaurant for this order',
                    'error_code': 'NO_RESTAURANT_FOUND'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if restaurant has coordinates
            if not restaurant.latitude or not restaurant.longitude:
                return Response({
                    'success': False,
                    'message': 'Restaurant location coordinates are not set. Please contact support.',
                    'error_code': 'RESTAURANT_NO_COORDINATES'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e),
                'error_code': 'MULTIPLE_RESTAURANTS'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # HANDLE ADDRESS LOGIC
        address_obj = None
        selected_address = None
        
        # If user is authenticated and address_id is provided
        if user and user.is_authenticated and address_id:
            try:
                selected_address = user.addresses.get(id=address_id)
                address_obj = selected_address
                
                # Populate order fields from selected address
                request.data['full_name'] = selected_address.full_name
                request.data['phone'] = selected_address.phone
                request.data['address'] = selected_address.address
                request.data['city'] = selected_address.city
                request.data['province'] = selected_address.province
                request.data['postal_code'] = selected_address.postal_code or ''
                
                # Add coordinates if available
                if selected_address.latitude and selected_address.longitude:
                    request.data['delivery_latitude'] = float(selected_address.latitude)
                    request.data['delivery_longitude'] = float(selected_address.longitude)
                    
            except Address.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'Address with ID {address_id} not found',
                    'error_code': 'ADDRESS_NOT_FOUND'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user default info if logged in
        default_info = self.get_user_default_info(user)
        
        # Prepare data for serializer
        data = request.data.copy()
        
        # For logged-in users, populate missing fields with default info (if no address selected)
        if user and user.is_authenticated:
            if not data.get('full_name'):
                data['full_name'] = default_info['full_name']
            if not data.get('phone'):
                data['phone'] = default_info['phone']
            if not data.get('email'):
                data['email'] = default_info['email']
            if not data.get('address'):
                data['address'] = default_info['address']
            if not data.get('city'):
                data['city'] = default_info['city']
            if not data.get('province'):
                data['province'] = default_info['province']
            if not data.get('postal_code'):
                data['postal_code'] = default_info['postal_code']
        
        # Validate data
        serializer = CreateOrderSerializer(
            data=data, 
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        # For guest users, guest_id is required
        guest_id = None
        if not user or not user.is_authenticated:
            guest_id = self.get_guest_id(request)
            print(f"CreateOrder - Guest ID: {guest_id}")
            
            if not guest_id:
                return Response({
                    'success': False,
                    'message': 'guest_id is required for guest checkout. Please provide X-Guest-ID header'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # For guests, ensure all required fields are present
            required_fields = ['full_name', 'phone', 'email', 'address', 'city']
            missing = []
            for field in required_fields:
                if not validated_data.get(field):
                    missing.append(field)
            
            if missing:
                return Response({
                    'success': False,
                    'message': f'Missing required fields: {", ".join(missing)}',
                    'missing_fields': missing
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate order totals
        subtotal = Decimal('0.00')
        order_items_data = []
        
        for cart_item in cart_items:
            item_total = cart_item.total_price
            subtotal += item_total
            order_items_data.append({
                'cart_item': cart_item,
                'menu_item': cart_item.menu_item,
                'quantity': cart_item.quantity,
                'price': cart_item.menu_item.price,
                'special_instructions': cart_item.special_instructions or ''
            })
        
        # Calculate delivery distance
        delivery_distance_km = Decimal('0.00')
        shipping_cost = Decimal('0.00')
        
        # Check if delivery location is provided
        if validated_data.get('delivery_latitude') and validated_data.get('delivery_longitude'):
            try:
                # Calculate distance between restaurant and delivery location
                distance = self.calculate_distance(
                    restaurant.latitude,
                    restaurant.longitude,
                    validated_data['delivery_latitude'],
                    validated_data['delivery_longitude']
                )
                delivery_distance_km = Decimal(str(distance))
                
                # Set shipping cost (free for ≤5km, NPR 100 for >5km)
                if distance <= 5:
                    shipping_cost = Decimal('0.00')
                else:
                    shipping_cost = Decimal('100.00')
                        
                print(f"Distance calculated: {distance} km, Shipping cost: {shipping_cost}")
                
            except Exception as e:
                print(f"Error calculating distance: {e}")
                shipping_cost = Decimal('0.00')
        else:
            print("No delivery coordinates provided for distance calculation")
        
        # Calculate tax
        tax_percentage = Decimal('0.00')
        tax_amount = Decimal('0.00')
        
        try:
            active_tax = TaxRate.objects.filter(is_active=True).first()
            if active_tax:
                tax_percentage = active_tax.tax
                taxable_amount = subtotal
                tax_amount = (taxable_amount * tax_percentage / 100).quantize(Decimal('0.01'))
                print(f"Using tax rate from TaxRate table: {tax_percentage}%, Tax amount: {tax_amount}")
        except Exception as e:
            print(f"Error fetching tax rate: {e}")

        discount = Decimal('0.00')
        total = subtotal + shipping_cost + tax_amount - discount
        
        # Get client IP for guest tracking
        guest_ip = self.get_client_ip(request) if not (user and user.is_authenticated) else None
        
        # Create order
        order = Order.objects.create(
            user=user if (user and user.is_authenticated) else None,
            guest_id=guest_id,
            guest_ip=guest_ip,
            address_obj=address_obj,  # Link to saved address if selected
            full_name=validated_data.get('full_name', ''),
            phone=validated_data.get('phone', ''),
            email=validated_data.get('email', ''),
            address=validated_data.get('address', ''),
            landmark=validated_data.get('landmark', ''),
            city=validated_data.get('city', ''),
            province=validated_data.get('province', ''),
            postal_code=validated_data.get('postal_code', ''),
            payment_method=validated_data.get('payment_method', 'cod'),
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            discount=discount,
            tax_percentage=tax_percentage,
            tax_amount=tax_amount,
            total=total,
            status='received',
            delivery_latitude=validated_data.get('delivery_latitude'),
            delivery_longitude=validated_data.get('delivery_longitude'),
            delivery_distance_km=delivery_distance_km
        )
        
        # Create order items with options
        for item_data in order_items_data:
            order_item = OrderItem.objects.create(
                order=order,
                menu_item=item_data['menu_item'],
                quantity=item_data['quantity'],
                price=item_data['price'],
                special_instructions=item_data['special_instructions']
            )
            
            # Copy options from cart item to order item
            if hasattr(item_data['cart_item'], 'options') and item_data['cart_item'].options.exists():
                order_item.options.set(item_data['cart_item'].options.all())
        
        # Clear ONLY the checked out items from cart
        checked_out_count = cart_items.count()
        cart_items.delete()
        
        # Get remaining cart count
        if user and user.is_authenticated:
            remaining_cart_count = Cart.objects.filter(user=user).count()
        else:
            remaining_cart_count = Cart.objects.filter(guest_id=guest_id, user__isnull=True).count()
        
        # Return order details
        order_data = OrderSerializer(order, context={'request': request}).data
        
        response_data = {
            'success': True,
            'message': 'Order created successfully',
            'order': order_data,
            'order_id': order.id,
            'order_number': order.order_number,
            'checked_out_items': checked_out_count,
            'remaining_cart_items': remaining_cart_count,
            'checkout_type': 'single' if single_cart_item_id else 'specific' if cart_item_ids else 'bulk',
            'delivery_details': {
                'distance_km': float(delivery_distance_km),
                'shipping_cost': float(shipping_cost),
                'shipping_policy': 'Free delivery for orders within 5km, NPR 100 for distances beyond 5km'
            }
        }
        
        # Add address info
        if selected_address:
            response_data['address_used'] = {
                'id': selected_address.id,
                'type': selected_address.address_type,
                'is_default': selected_address.is_default
            }
        
        # Add checkout-specific info
        if single_cart_item_id:
            response_data['checked_out_cart_item_id'] = single_cart_item_id
        elif cart_item_ids:
            response_data['checked_out_cart_item_ids'] = cart_item_ids
        
        return Response(response_data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    """
    Get order details by ID or order number for Flutter app
    GET /api/orders/<identifier>/
    
    Query parameters (for guest access):
    - guest_id: UUID from Flutter app
    - email: Email for guest order lookup
    - token: Lookup token from previous response
    
    Headers for authenticated users:
        Authorization: Bearer <jwt_token>
    Headers for guest users:
        X-Guest-ID: <uuid_from_flutter>
    """
    permission_classes = [AllowAny]
    
    def get_authenticated_user(self, request):
        """Try to authenticate user from JWT token - SAME as other views"""
        try:
            # Try JWT authentication
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception as e:
            # JWT authentication failed, but that's ok for guest users
            pass
        
        # Check if already authenticated through session
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_guest_id(self, request):
        """Get guest_id from request headers or query params"""
        # Try headers first (recommended for Flutter)
        guest_id = request.headers.get('X-Guest-ID')
        
        # Fallback to query parameter
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        # Fallback to request body
        if not guest_id and request.method != 'GET':
            guest_id = request.data.get('guest_id')
        
        return guest_id
    
    def validate_lookup_token(self, order, token):
        """Validate lookup token for guest order access"""
        from django.core.cache import cache
        cache_key = f"order_lookup_{order.id}"
        stored_token = cache.get(cache_key)
        return stored_token == token
    
    def generate_lookup_token(self, order):
        """Generate a temporary token for guest order access"""
        import hashlib
        import time
        from django.core.cache import cache
        
        expiry = int(time.time()) + 86400  # 24 hours
        token_data = f"{order.id}:{order.order_number}:{expiry}:{order.guest_id}"
        token_hash = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        
        # Store in cache for validation
        cache_key = f"order_lookup_{order.id}"
        cache.set(cache_key, token_hash, timeout=86400)
        
        return token_hash
    
    def get_order_timeline(self, order):
        """Generate order timeline for better user experience"""
        timeline = []
        
        # Order placed
        timeline.append({
            'status': 'order_placed',
            'title': 'Order Placed',
            'description': f'Order #{order.order_number} has been received',
            'timestamp': order.created_at,
            'formatted_time': order.created_at.strftime("%Y-%m-%d %H:%M"),
            'completed': True,
            'icon': 'check_circle'
        })
        
        # Payment status
        if order.payment_status == 'paid':
            timeline.append({
                'status': 'payment_confirmed',
                'title': 'Payment Confirmed',
                'description': f'Payment of {order.total} received via {order.get_payment_method_display()}',
                'timestamp': order.updated_at,
                'formatted_time': order.updated_at.strftime("%Y-%m-%d %H:%M"),
                'completed': True,
                'icon': 'payment'
            })
        
        # Order status timeline
        status_timeline_map = {
            'preparing': {
                'title': 'Preparing',
                'description': 'Restaurant is preparing your order',
                'icon': 'restaurant'
            },
            'ready': {
                'title': 'Ready for Pickup',
                'description': 'Your order is ready and will be picked up soon',
                'icon': 'restaurant_menu'
            },
            'picked_up': {
                'title': 'Picked Up',
                'description': 'Delivery partner has picked up your order',
                'icon': 'delivery_dining'
            },
            'in_transit': {
                'title': 'On The Way',
                'description': 'Your order is on the way to your address',
                'icon': 'local_shipping'
            },
            'delivered': {
                'title': 'Delivered',
                'description': 'Your order has been delivered successfully',
                'icon': 'celebration'
            }
        }
        
        status_reached = False
        for status_key, status_info in status_timeline_map.items():
            if order.status == status_key or (order.status == 'delivered' and not status_reached):
                timeline.append({
                    'status': status_key,
                    'title': status_info['title'],
                    'description': status_info['description'],
                    'timestamp': getattr(order, f'{status_key}_at', None) or order.updated_at,
                    'formatted_time': (getattr(order, f'{status_key}_at', None) or order.updated_at).strftime("%Y-%m-%d %H:%M"),
                    'completed': order.status in [status_key, 'delivered'],
                    'icon': status_info['icon']
                })
                status_reached = True
        
        # Cancellation
        if order.status == 'cancelled':
            timeline.append({
                'status': 'cancelled',
                'title': 'Cancelled',
                'description': f'Order cancelled on {order.cancelled_at.strftime("%Y-%m-%d %H:%M") if order.cancelled_at else "Unknown date"}',
                'timestamp': order.cancelled_at,
                'formatted_time': order.cancelled_at.strftime("%Y-%m-%d %H:%M") if order.cancelled_at else None,
                'completed': True,
                'icon': 'cancel'
            })
        
        return timeline
    
    def get(self, request, identifier):
        # First try to get authenticated user (FIXED)
        user = self.get_authenticated_user(request)
        
        # Debug logging
        print(f"OrderDetailView - User authenticated: {user.is_authenticated if user else False}")
        print(f"OrderDetailView - User: {user.email if user else 'None'}")
        print(f"OrderDetailView - Authorization header: {request.headers.get('Authorization')}")
        
        # Try to find order by ID or order_number
        try:
            if identifier.isdigit():
                order = Order.objects.get(id=identifier)
            else:
                order = Order.objects.get(order_number=identifier)
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Order not found',
                'error_code': 'NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get guest_id for guest users (FIXED)
        guest_id = None
        if not user or not user.is_authenticated:
            guest_id = self.get_guest_id(request)
        
        lookup_token = request.query_params.get('token')
        email = request.query_params.get('email')
        
        is_authorized = False
        auth_method = None
        
        # Case 1: Authenticated user owns the order (FIXED)
        if user and user.is_authenticated and order.user == user:
            is_authorized = True
            auth_method = 'authenticated_user'
            print(f"OrderDetailView - Authorized: authenticated user {user.email}")
        
        # Case 2: Guest user owns the order (check by guest_id)
        elif (not user or not user.is_authenticated) and order.guest_id and order.guest_id == guest_id:
            is_authorized = True
            auth_method = 'guest_id'
            print(f"OrderDetailView - Authorized: guest_id match")
        
        # Case 3: Staff/Admin can view any order
        elif user and user.is_authenticated and user.is_staff:
            is_authorized = True
            auth_method = 'staff'
            print(f"OrderDetailView - Authorized: staff user")
        
        # Case 4: Valid lookup token provided
        elif (not user or not user.is_authenticated) and lookup_token and self.validate_lookup_token(order, lookup_token):
            is_authorized = True
            auth_method = 'lookup_token'
            print(f"OrderDetailView - Authorized: lookup token")
        
        # Case 5: Guest order accessed via email (for order tracking)
        elif (not user or not user.is_authenticated) and order.email and email and order.email.lower() == email.lower():
            is_authorized = True
            auth_method = 'email'
            print(f"OrderDetailView - Authorized: email match")
        
        if not is_authorized:
            # Provide helpful error message
            error_message = 'Unauthorized to view this order'
            error_code = 'UNAUTHORIZED'
            
            if order.user and not user:
                error_message = 'This order belongs to a registered user. Please login to view it.'
                error_code = 'LOGIN_REQUIRED'
            elif order.is_guest_order and not guest_id:
                error_message = 'Guest ID required to view this order. Please provide X-Guest-ID header.'
                error_code = 'GUEST_ID_REQUIRED'
            elif order.is_guest_order and guest_id and order.guest_id != guest_id:
                error_message = 'This guest order belongs to a different guest session.'
                error_code = 'GUEST_SESSION_MISMATCH'
            
            return Response({
                'success': False,
                'message': error_message,
                'error_code': error_code,
                'is_guest_order': order.is_guest_order,
                'has_user': order.user is not None
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Serialize order with full details
        serializer = OrderSerializer(order, context={'request': request})
        
        # Get timeline for the order
        timeline = self.get_order_timeline(order)
        
        # Prepare response
        response_data = {
            'success': True,
            'data': serializer.data,
            'timeline': timeline,
            'auth_method': auth_method
        }
        
        # Generate lookup token for guest users (valid for 24 hours)
        if order.is_guest_order and (not user or not user.is_authenticated) and auth_method != 'lookup_token':
            lookup_token = self.generate_lookup_token(order)
            response_data['lookup_token'] = lookup_token
            response_data['lookup_token_expiry'] = '24 hours'
        
        return Response(response_data, status=status.HTTP_200_OK)


class UserOrdersView(APIView):
    """
    Get all orders for authenticated user
    GET /api/orders/my-orders/
    
    Query Parameters:
    - status: Filter by order status (received, preparing, ready, picked_up, assigned, in_transit, delivered, cancelled, refunded)
    - payment_status: Filter by payment status (unpaid, paid, failed, refunded)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - ordering: Sort orders (created_at, -created_at, total, -total)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Base queryset
        orders = Order.objects.filter(user=request.user)
        
        # Filter by order status
        status_filter = request.query_params.get('status')
        if status_filter:
            valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
            if status_filter in valid_statuses:
                orders = orders.filter(status=status_filter)
            else:
                return Response({
                    'success': False,
                    'message': f'Invalid status. Valid choices: {", ".join(valid_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter by payment status
        payment_status_filter = request.query_params.get('payment_status')
        if payment_status_filter:
            valid_payment_statuses = [choice[0] for choice in Order.PAYMENT_STATUS_CHOICES]
            if payment_status_filter in valid_payment_statuses:
                orders = orders.filter(payment_status=payment_status_filter)
            else:
                return Response({
                    'success': False,
                    'message': f'Invalid payment status. Valid choices: {", ".join(valid_payment_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Date range filtering
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if from_date:
            try:
                from_date_parsed = timezone.datetime.strptime(from_date, '%Y-%m-%d')
                orders = orders.filter(created_at__date__gte=from_date_parsed)
            except ValueError:
                return Response({
                    'success': False,
                    'message': 'Invalid from_date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if to_date:
            try:
                to_date_parsed = timezone.datetime.strptime(to_date, '%Y-%m-%d')
                orders = orders.filter(created_at__date__lte=to_date_parsed)
            except ValueError:
                return Response({
                    'success': False,
                    'message': 'Invalid to_date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Apply ordering
        ordering = request.query_params.get('ordering', '-created_at')
        valid_ordering_fields = ['created_at', '-created_at', 'total', '-total', 'order_number', '-order_number']
        if ordering in valid_ordering_fields:
            orders = orders.order_by(ordering)
        else:
            orders = orders.order_by('-created_at')
        
        # Get order summary
        summary = {
            'total_orders': orders.count(),
            'total_spent': float(orders.aggregate(total=models.Sum('total'))['total'] or 0),
            'active_orders': orders.exclude(status__in=['delivered', 'cancelled', 'refunded']).count(),
            'pending_payment': orders.filter(payment_status='unpaid').count(),
        }
        
        if summary['total_orders'] > 0:
            summary['average_order_value'] = summary['total_spent'] / summary['total_orders']
        
        # Status counts
        for status_code, status_label in Order.STATUS_CHOICES:
            summary[f'status_{status_code}'] = orders.filter(status=status_code).count()
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Limit page size to prevent abuse
        if page_size > 100:
            page_size = 100
        if page_size < 1:
            page_size = 20
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = orders.count()
        paginated_orders = orders[start:end]
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        serializer = OrderListSerializer(paginated_orders, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'summary': summary,
            'pagination': {
                'current_page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': end < total_count,
                'has_previous': page > 1,
                'next_page': page + 1 if end < total_count else None,
                'previous_page': page - 1 if page > 1 else None,
            },
            'data': serializer.data
        })

class GuestOrderLookupView(APIView):
    """
    Lookup guest order by order number (and optionally email)
    POST /api/orders/guest-lookup/
    
    For Flutter app - No session dependency
    
    Request body:
        - order_number: (required) Order number
        - email: (optional) Email for additional verification
        - guest_id: (optional) Guest ID from app
    
    Headers (for guest_id lookup):
        X-Guest-ID: <uuid_from_flutter>
    """
    permission_classes = [AllowAny]
    
    def get_guest_id(self, request):
        """Get guest_id from request headers"""
        guest_id = request.headers.get('X-Guest-ID')
        
        if not guest_id:
            guest_id = request.data.get('guest_id')
        
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        return guest_id
    
    def post(self, request):
        order_number = request.data.get('order_number')
        email = request.data.get('email')  # Now optional
        guest_id = self.get_guest_id(request)
        
        # Validate required fields
        if not order_number:
            return Response({
                'success': False,
                'message': 'Order number is required',
                'error_code': 'MISSING_ORDER_NUMBER'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # First try to find order by order_number
            order = Order.objects.get(order_number=order_number)
            
            # Check if this is a guest order
            if order.user is not None:
                return Response({
                    'success': False,
                    'message': 'This order belongs to a registered user. Please login to view it.',
                    'error_code': 'REGISTERED_USER_ORDER',
                    'requires_login': True
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Verify access using email OR guest_id
            has_access = False
            access_method = None
            
            # Method 1: Check by email
            if email and order.email and order.email.lower() == email.lower():
                has_access = True
                access_method = 'email'
            
            # Method 2: Check by guest_id
            elif guest_id and order.guest_id and order.guest_id == guest_id:
                has_access = True
                access_method = 'guest_id'
            
            # Method 3: If no email or guest_id provided, still allow basic access
            # but with limited info (privacy consideration)
            elif not email and not guest_id:
                has_access = True
                access_method = 'basic'
            
            if not has_access:
                return Response({
                    'success': False,
                    'message': 'Unable to verify order ownership. Please provide valid email or guest_id.',
                    'error_code': 'VERIFICATION_FAILED'
                }, status=status.HTTP_403_FORBIDDEN)
            
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Order not found. Please check your order number.',
                'error_code': 'ORDER_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Generate lookup token for future access
        lookup_token = self.generate_lookup_token(order)
        
        # Serialize order data
        order_data = {
            'id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'payment_method': order.payment_method,
            'payment_method_display': order.get_payment_method_display(),
            'payment_status': order.payment_status,
            'payment_status_display': order.get_payment_status_display(),
            'created_at': order.created_at,
            'formatted_created_at': order.created_at.strftime("%Y-%m-%d %H:%M"),
            'estimated_delivery_date': order.estimated_delivery_date,
            
            # Pricing
            'subtotal': float(order.subtotal),
            'subtotal_formatted': f"Rs. {order.subtotal:,.2f}",
            'shipping_cost': float(order.shipping_cost),
            'tax_amount': float(order.tax_amount),
            'discount': float(order.discount),
            'total': float(order.total),
            'total_formatted': f"Rs. {order.total:,.2f}",
            
            # Delivery info (hide email if access_method is 'basic')
            'delivery_address': {
                'full_name': order.full_name,
                'phone': order.phone,
                'email': order.email if access_method != 'basic' else None,
                'address': order.address,
                'city': order.city,
                'province': order.province,
                'postal_code': order.postal_code
            },
            
            # Items (limited info for basic access)
            'items': self.get_order_items(order, access_method),
            
            # Actions
            'can_cancel': order.can_cancel(),
            'can_request_refund': order.can_request_refund(),
            
            # Access info
            'access_method': access_method
        }
        
        response_data = {
            'success': True,
            'message': 'Order found successfully',
            'data': order_data
        }
        
        # Include lookup token for future access (valid for 24 hours)
        if access_method != 'basic':
            response_data['lookup_token'] = lookup_token
            response_data['lookup_token_expiry'] = '24 hours'
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def get_order_items(self, order, access_method):
        """Get order items with appropriate level of detail based on access method"""
        items = []
        
        for item in order.items.all():
            item_data = {
                'id': item.id,
                'menu_item_name': item.menu_item.name if item.menu_item else 'Unknown Item',
                'quantity': item.quantity,
                'price': float(item.price),
                'price_formatted': f"Rs. {item.price:,.2f}",
                'total': float(item.price * item.quantity),
                'total_formatted': f"Rs. {item.price * item.quantity:,.2f}"
            }
            
            # Add options if they exist
            if hasattr(item, 'options') and item.options.exists():
                item_data['options'] = [
                    {
                        'name': option.name,
                        'price_adjustment': float(option.price_adjustment)
                    }
                    for option in item.options.all()
                ]
            
            # Hide special instructions for basic access
            if access_method != 'basic' and item.special_instructions:
                item_data['special_instructions'] = item.special_instructions
            
            items.append(item_data)
        
        return items
    
    def generate_lookup_token(self, order):
        """Generate a temporary token for guest order access"""
        import hashlib
        import time
        from django.core.cache import cache
        
        expiry = int(time.time()) + 86400  # 24 hours
        token_data = f"{order.id}:{order.order_number}:{expiry}:{order.guest_id}"
        token_hash = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        
        # Store in cache for validation
        cache_key = f"order_lookup_{order.id}"
        cache.set(cache_key, token_hash, timeout=86400)
        
        return token_hash


class CancelOrderView(APIView):
    """
    Cancel an order (for customers only - registered users and guests)
    POST /api/orders/<order_id>/cancel/
    
    For Flutter app:
    - Authenticated users: Use JWT token in Authorization header
    - Guest users: Must provide X-Guest-ID header
    
    Both can cancel using the order_id from the order details response
    """
    permission_classes = [AllowAny]
    
    def get_authenticated_user(self, request):
        """Try to authenticate user from JWT token"""
        try:
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                return user
        except Exception as e:
            pass
        
        if request.user and request.user.is_authenticated:
            return request.user
        
        return None
    
    def get_guest_id(self, request):
        """Get guest_id from request headers"""
        guest_id = request.headers.get('X-Guest-ID')
        
        if not guest_id:
            guest_id = request.data.get('guest_id')
        
        if not guest_id:
            guest_id = request.query_params.get('guest_id')
        
        return guest_id
    
    def generate_lookup_token(self, order):
        """Generate a temporary token for guest order access"""
        import hashlib
        import time
        from django.core.cache import cache
        
        expiry = int(time.time()) + 86400  # 24 hours
        token_data = f"{order.id}:{order.order_number}:{expiry}:{order.guest_id}"
        token_hash = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        
        cache_key = f"order_lookup_{order.id}"
        cache.set(cache_key, token_hash, timeout=86400)
        
        return token_hash
    
    def post(self, request, order_id):
        # First try to get authenticated user
        user = self.get_authenticated_user(request)
        
        # Debug logging
        print(f"CancelOrder - User authenticated: {user.is_authenticated if user else False}")
        print(f"CancelOrder - Order ID: {order_id}")
        
        # Get the order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Order not found',
                'error_code': 'ORDER_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # For AUTHENTICATED users
        if user and user.is_authenticated:
            # Check if the authenticated user owns this order
            if order.user != user:
                return Response({
                    'success': False,
                    'message': 'You can only cancel your own orders.',
                    'error_code': 'NOT_ORDER_OWNER'
                }, status=status.HTTP_403_FORBIDDEN)
            
            auth_method = 'authenticated_user'
            print(f"CancelOrder - Authorized: authenticated user owns this order")
        
        # For GUEST users
        else:
            # Guest users must provide guest_id
            guest_id = self.get_guest_id(request)
            print(f"CancelOrder - Guest ID provided: {guest_id}")
            
            if not guest_id:
                return Response({
                    'success': False,
                    'message': 'Guest ID is required to cancel this order. Please provide X-Guest-ID header.',
                    'error_code': 'GUEST_ID_REQUIRED'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if this is a guest order
            if order.user is not None:
                return Response({
                    'success': False,
                    'message': 'This order belongs to a registered user. Please login to cancel it.',
                    'error_code': 'LOGIN_REQUIRED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if guest_id matches
            if order.guest_id != guest_id:
                return Response({
                    'success': False,
                    'message': 'The guest ID provided does not match the order. Please use the correct guest ID.',
                    'error_code': 'GUEST_SESSION_MISMATCH'
                }, status=status.HTTP_403_FORBIDDEN)
            
            auth_method = 'guest_user'
            print(f"CancelOrder - Authorized: guest user owns this order")
        
        # Check if order can be cancelled
        if not order.can_cancel():
            return Response({
                'success': False,
                'message': f'Order cannot be cancelled. Current status: {order.get_status_display()}',
                'error_code': 'CANNOT_CANCEL',
                'current_status': order.status,
                'current_status_display': order.get_status_display(),
                'allowed_statuses': ['received', 'preparing']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cancel the order
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.save()
        
        # Handle refund if payment was made
        refund_status = None
        if order.payment_status == 'paid':
            order.payment_status = 'refunded'
            order.refunded_at = timezone.now()
            order.save()
            refund_status = 'refunded'
        elif order.payment_status == 'unpaid':
            refund_status = 'no_charge'
        
        print(f"CancelOrder - Order cancelled successfully: {order.order_number}")
        
        # Prepare response
        response_data = {
            'success': True,
            'message': 'Order cancelled successfully',
            'refund_status': refund_status,
            'auth_method': auth_method,
            'order_id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'cancelled_at': order.cancelled_at
        }
        
        # Generate lookup token for guest users
        if auth_method == 'guest_user':
            lookup_token = self.generate_lookup_token(order)
            response_data['lookup_token'] = lookup_token
            response_data['lookup_token_expiry'] = '24 hours'
        
        # Include serialized order data
        serializer = OrderSerializer(order, context={'request': request})
        response_data['data'] = serializer.data
        
        return Response(response_data, status=status.HTTP_200_OK)
# ================================================================
# End of Order API Views
# ================================================================