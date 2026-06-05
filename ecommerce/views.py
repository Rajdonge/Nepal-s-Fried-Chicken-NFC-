
from django.shortcuts import render,redirect
from django.contrib.auth.models import User
import json
import os
import uuid
import random
import string
from decimal import Decimal
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F
from django.conf import settings
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import AccessToken

from dashboard.models import (
    UserRole,
    UserProfile,
    Slider,
    Banner,
    CuisineType,
    MenuItem,
    MenuItemOption,
    Cart,
    Restaurant,
    OTPVerification,
    Order,
    OrderItem,
    Coupon,
    CouponUsage,
    Contact,
    Invoice,
    RestaurantReview,
    TaxRate,
    RestaurantCommission,
    MenuItemImage,
    MenuSection,
    FoodTag,
    MenuItemReview,
)


from .recommender import get_recommendations


# ===================
# Home & Search
# ===================
def home_page(request):
    sliders = Slider.objects.filter(is_active=True).order_by('-created_at')[:5]
    banners = Banner.objects.filter(is_active=True, page="home")
    cuisines = CuisineType.objects.filter(is_active=True, is_featured=True).order_by('order')[:12]
    
    # Featured Menu Items Pagination
    featured_items = MenuItem.objects.filter(is_available=True, is_featured=True, restaurant__is_active=True).order_by('-created_at')
    featured_paginator = Paginator(featured_items, 18)
    featured_page_number = request.GET.get('featured_page', 1)
    featured_items_page = featured_paginator.get_page(featured_page_number)
    
    # Popular Restaurants
    popular_restaurants = Restaurant.objects.filter(is_active=True, is_open=True).order_by('-created_at')[:12]
      # All Menu Items (non-featured) Pagination
    all_items = MenuItem.objects.filter(is_available=True, restaurant__is_active=True).order_by('-created_at')
    all_paginator = Paginator(all_items, 18)
    all_page_number = request.GET.get('all_page', 1)
    all_items_page = all_paginator.get_page(all_page_number)
   

    context = {
        'sliders': sliders,
        'banners': banners,
        'cuisines': cuisines,
        'featured_items': featured_items_page,
        'popular_restaurants': popular_restaurants,
        'all_items': all_items_page,
    }
    return render(request, 'website/pages/home.html', context)


# ----------------------------
# PWA root assets
# ----------------------------
from django.http import HttpResponse, Http404

def service_worker(request):
    """Serve the service worker from /service-worker.js so it can control the whole origin."""
    file_path = os.path.join(settings.BASE_DIR, 'static', 'pwa', 'service-worker.js')
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript')
        # Keep short cache for deployment updates
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    except FileNotFoundError:
        raise Http404('service-worker.js not found')


def web_manifest(request):
    """Serve the web manifest at /manifest.json for correct discovery and TWA tooling."""
    file_path = os.path.join(settings.BASE_DIR, 'static', 'pwa', 'manifest.json')
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/manifest+json')
    except FileNotFoundError:
        raise Http404('manifest.json not found')


def assetlinks(request):
    """Serve the Digital Asset Links file at /.well-known/assetlinks.json
    so Android can verify app <-> website association for TWA.
    """
    file_path = os.path.join(settings.BASE_DIR, 'static', '.well-known', 'assetlinks.json')
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/json')
        # Asset Links can be cached but keep TTL moderate; apps reverify on install
        response['Cache-Control'] = 'public, max-age=86400'
        return response
    except FileNotFoundError:
        raise Http404('assetlinks.json not found')



def search_page(request):
    query = request.GET.get('q', '').strip()
    menu_items = MenuItem.objects.filter(is_available=True, restaurant__is_active=True)

    if query:
        menu_items = menu_items.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(restaurant__restaurant_name__icontains=query)
        ).distinct().order_by('-created_at')

    # Pagination
    paginator = Paginator(menu_items, 24) 
    page_number = request.GET.get('page', 1)
    items_page = paginator.get_page(page_number)

    context = {
        'query': query,
        'products': items_page,
    }
    return render(request, 'website/pages/search.html', context)



def all_collections(request):
    query = request.GET.get('q', '').strip()
    products = MenuItem.objects.filter(is_available=True).order_by('-created_at')
    restaurants = Restaurant.objects.filter(is_active=True).order_by('restaurant_name')
    
    # Apply search filter
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(restaurant__restaurant_name__icontains=query)
        ).distinct()
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'restaurants': restaurants,
        'query': query,
    }
    return render(request, 'website/pages/all_collections.html', context)

def new_arrivals_page(request):
    # Calculate the date 29 days ago
    one_month_ago = timezone.now() - timedelta(days=29)
    new_items = MenuItem.objects.filter(
        is_available=True,
        restaurant__is_active=True,
        created_at__gte=one_month_ago
    ).order_by('-created_at')
    
    paginator = Paginator(new_items, 12)  
    page_number = request.GET.get('page', 1)
    new_items_page = paginator.get_page(page_number)

    context = {
        'products': new_items_page,
    }
    return render(request, 'website/pages/new_arrivals.html', context)




import string

# ===================
# Restaurant Registration
# ===================
def become_restaurant(request):
    if request.method == 'POST':
        try:
            print(request.POST)
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email', '').strip().lower()
            if User.objects.filter(email=email,is_active=True).exists():
                messages.error(request,'User already exists')
                return redirect('restaurant_partner_page')
            

            # Restaurant info
            restaurant_name = request.POST.get('restaurant_name')
            description = request.POST.get('description')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            city = request.POST.get('city')
            province = request.POST.get('province')
            pan_number = request.POST.get('pan_number')
            citizenship_number = request.POST.get('citizenship_number')
            # Files
            logo = request.FILES.get('logo')
            banner = request.FILES.get('banner')
            pan_document = request.FILES.get('pan_document')
            citizenship_front = request.FILES.get('citizenship_front')
            citizenship_back = request.FILES.get('citizenship_back')
            company_registration = request.FILES.get('company_registration')
            qr_image = request.FILES.get('qr_image')

            # Update user info
            user, _ = User.objects.get_or_create(email=email)
            user.username = email
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.is_active = False
            user.save()
        
            # Create restaurant
            restaurant = Restaurant.objects.create(
                user=user,
                restaurant_name=restaurant_name,
                banner=banner,
                description=description or "",
                phone=phone,
                address=address,
                city=city or "",
                province=province or "",
                pan_number=pan_number,
                logo=logo,
                pan_document=pan_document,
                citizenship_number=citizenship_number,
                citizenship_front=citizenship_front,
                citizenship_back=citizenship_back,
                company_registration=company_registration,
                qr_image=qr_image
            )
            random_password = ''.join(random.choices(string.ascii_letters + string.digits + "@#$%&", k=10))
            user.set_password(random_password)
            user.save()

            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            otp_obj, _ = OTPVerification.objects.get_or_create(user=user)
            otp_obj.otp_code = otp_code
            otp_obj.save()
            
            # Send email
            try:
                send_mail(
                    subject="Your OTP Code - HelloBajar Restaurant Verification",
                    message=f"Hello {first_name},\n\nYour OTP for restaurant registration is: {otp_code}\n\nThank you for joining HelloBajar!",
                    from_email="hellobajar@gmail.com",
                    recipient_list=[email],
                    fail_silently=False
                )
                
            except Exception:
                messages.error(request, "Failed to send OTP. Please check your email address.")
                return redirect('restaurant_partner_page')
            
            request.session['user_email'] = email
            messages.success(request, "Restaurant registration submitted! Please verify OTP sent to your email.")
            return redirect('verify_otp_page')

        except Exception as e:
            messages.error(request, f"Something went wrong: {str(e)}")
            return redirect('restaurant_partner_page')

    return render(request, 'website/pages/restaurant_partner.html')



# ===================
# Privacy Policy
# ==================

def privacy_policy(request):
    return render(request, 'website/pages/privacy_policy.html')



# ===================
# Restaurant Listing
# ===================
def restaurants(request):
    # Fetch all active and verified restaurants
    restaurants = Restaurant.objects.filter(is_active=True, verification_status='approved').order_by('restaurant_name')
    search_term = request.GET.get('search', '').strip()
    cuisine_id = request.GET.get('cuisine', '')

    if search_term:
        restaurants = restaurants.filter(restaurant_name__icontains=search_term)
    
    paginator = Paginator(restaurants, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'featured_vendors': restaurants[:4],  # First 4 as featured
        'vendors': page_obj,                  # Paginated list
    }
    return render(request, 'website/pages/restaurants.html', context)


def restaurant_details(request, slug=None):
    """Display restaurant details with their menu items"""
    if slug:
        try:
            restaurant = Restaurant.objects.select_related('user').prefetch_related('menu_items').get(slug=slug, is_active=True)
            menu_items = restaurant.menu_items.filter(is_available=True).order_by('-created_at')[:12]
            menu_sections = restaurant.menu_sections.filter(is_active=True)
            
            context = {
                'restaurant': restaurant,
                'menu_items': menu_items,
                'menu_sections': menu_sections,
            }
            return render(request, 'website/pages/restaurant_details.html', context)
        except Restaurant.DoesNotExist:
            messages.error(request, 'Restaurant not found')
            return redirect('restaurants')
    else:
        return render(request, 'website/pages/restaurant_details.html')
    
    
    

# ===================
# Cuisine Type details
# ===================
def cuisine_details(request, slug):
    cuisine = get_object_or_404(CuisineType, slug=slug, is_active=True)
    
    # Get all restaurants serving this cuisine
    restaurants = Restaurant.objects.filter(
        is_active=True, 
        cuisines=cuisine
    ).order_by('restaurant_name')
    
    # Get all active cuisines for navigation
    cuisines = CuisineType.objects.filter(is_active=True)
    
    context = {
        'cuisine': cuisine,
        'restaurants': restaurants,
        'cuisines': cuisines,
    }
    
    return render(request, 'website/pages/cuisine_details.html', context)



# ==============================
#   Cart
# ==============================

def get_session_key(request):
    """Get or create a session key for guest users"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key




# ===================
# Cart Management
# ===================
def carts(request):
    # --- Get user's cart items with optimized queries ---
    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(
            user=request.user
        ).select_related(
            'menu_item',
            'menu_item__restaurant'
        ).prefetch_related(
            'options'  # Prefetch all options (ManyToMany)
        )
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart_items = Cart.objects.filter(
            user__isnull=True, 
            session_key=session_key
        ).select_related(
            'menu_item',
            'menu_item__restaurant'
        ).prefetch_related(
            'options'
        )

    # --- Calculate totals ---
    total_items = sum(item.quantity for item in cart_items)
    
    # Use the model's get_total_price() which handles options
    sub_total_price = sum(item.get_total_price() for item in cart_items)

    # --- Group by restaurant for delivery fee ---
    restaurant_groups = {}
    for item in cart_items:
        restaurant = item.menu_item.restaurant
        if restaurant not in restaurant_groups:
            restaurant_groups[restaurant] = []
        restaurant_groups[restaurant].append(item)
    
    # Get default delivery fee from first zone or use 0
    total_delivery_fee = Decimal('0.00')
    for restaurant in restaurant_groups.keys():
        # Get first delivery zone for this restaurant
        zone = restaurant.delivery_zones.first()
        if zone:
            total_delivery_fee += zone.delivery_fee
  

    # --- Get tax rate ---
    tax_obj = TaxRate.objects.first()
    tax_rate = tax_obj.tax if tax_obj else Decimal('0.00')

    # --- Calculate tax on subtotal + delivery ---
    tax_amount = (sub_total_price + total_delivery_fee) * (tax_rate / Decimal('100'))
    tax_amount = tax_amount.quantize(Decimal('0.01'))

    # --- Total price ---
    total_price = (sub_total_price + total_delivery_fee + tax_amount).quantize(Decimal('0.01'))

    # --- Additional context for better UI ---
    # Add options details to each cart item for template display
    for item in cart_items:
        # Get all options for this cart item
        item.options_list = list(item.options.all())
        # Calculate item price with options
        item.unit_price = item.get_item_price()
        item.line_total = item.get_total_price()

    context = {
        'cart_items': cart_items,
        'total_items': total_items,
        'sub_total_price': sub_total_price,
        'delivery_fee': total_delivery_fee,
        'tax_amount': tax_amount,
        'tax_rate': tax_rate,
        'total_price': total_price,
    }

    return render(request, "website/pages/cart.html", context)




@csrf_exempt
@require_http_methods(["POST"])
def add_to_cart(request):
    """Add menu item to cart with multiple options (auth + guest)"""
    try:
        data = json.loads(request.body)
        menu_item_id = data.get('menu_item_id')
        quantity = int(data.get('quantity', 1))
        option_ids = data.get('option_ids', [])  # Now accepts array of option IDs
        special_instructions = data.get('special_instructions', '')
        
        # Determine user or session
        user = request.user if request.user.is_authenticated else None
        session_key = None if user else get_session_key(request)
        
        # Validate menu item
        try:
            menu_item = MenuItem.objects.get(id=menu_item_id, is_available=True)
        except MenuItem.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'Menu item not found'
            }, status=404)

        # Validate options if provided
        selected_options = []
        
        if option_ids:
            for option_id in option_ids:
                try:
                    option = MenuItemOption.objects.get(
                        id=option_id, 
                        menu_item=menu_item,
                        is_available=True
                    )
                    selected_options.append(option)
                        
                except MenuItemOption.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': f'Invalid option selected'
                    }, status=400)
        
        # Find existing cart items with same menu item and options
        if user:
            existing_cart_items = Cart.objects.filter(user=user, menu_item=menu_item)
        else:
            existing_cart_items = Cart.objects.filter(
                session_key=session_key, 
                menu_item=menu_item
            )
        
        # Check for exact options match
        cart_item = None
        for item in existing_cart_items:
            item_options = set(item.options.all())
            if item_options == set(selected_options):
                cart_item = item
                break
        
        if cart_item:
            # Update existing cart item
            cart_item.quantity += quantity
            cart_item.save()
        else:
            # Create new cart item
            cart_item = Cart.objects.create(
                user=user,
                session_key=session_key,
                menu_item=menu_item,
                quantity=quantity,
                special_instructions=special_instructions
            )
            # Add selected options (ManyToMany)
            if selected_options:
                cart_item.options.set(selected_options)
        
        # Calculate cart count
        if user:
            cart_count = Cart.objects.filter(user=user)
        else:
            cart_count = Cart.objects.filter(session_key=session_key)
        
        total_items = sum(item.quantity for item in cart_count)
        
        # Build options display string
        option_names = ', '.join([o.name for o in selected_options]) if selected_options else ''
        item_display = f"{menu_item.name} ({option_names})" if option_names else menu_item.name

        return JsonResponse({
            'success': True,
            'message': f'{quantity} × {item_display} added to cart',
            'cart_count': total_items,
            'item_total': float(cart_item.get_total_price())
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'message': 'Invalid JSON data'
        }, status=400)
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid quantity'
        }, status=400)
    except Exception as e:
        # Log the error for debugging
        print(f"Cart Error: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': 'Error adding to cart'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_cart_item(request):
    """Update cart item quantity (auth + guest)"""
    try:
        data = json.loads(request.body)
        cart_item_id = data.get('cart_item_id')
        quantity = int(data.get('quantity', 1))

        user = request.user if request.user.is_authenticated else None
        session_key = None if user else get_session_key(request)

        try:
            cart_item = Cart.objects.get(id=cart_item_id, user=user, session_key=session_key)
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Cart item not found'}, status=404)

        if quantity <= 0:
            cart_item.delete()
            action = 'removed'
        else:
            cart_item.quantity = quantity
            cart_item.save()
            action = 'updated'

        # Get updated cart totals
        cart_items = Cart.objects.filter(user=user) if user else Cart.objects.filter(session_key=session_key)

        # Group by restaurant and get delivery fee
        restaurant_groups = {}
        for item in cart_items:
            restaurant = item.menu_item.restaurant
            if restaurant not in restaurant_groups:
                restaurant_groups[restaurant] = []
            restaurant_groups[restaurant].append(item)

        total_delivery_fee = Decimal('0.00')
        for restaurant in restaurant_groups.keys():
            zone = restaurant.delivery_zones.first()
            if zone:
                total_delivery_fee += zone.delivery_fee

        total_items = sum(item.quantity for item in cart_items)
        sub_total = sum(item.get_total_price() for item in cart_items)
        tax_obj = TaxRate.objects.first()
        tax_rate = tax_obj.tax if tax_obj else 0
        tax_amount = (sub_total + total_delivery_fee) * (tax_rate / 100)
        total_price = sub_total + total_delivery_fee + tax_amount

        return JsonResponse({
            'success': True,
            'message': f'Cart item {action} successfully',
            'item_total': float(cart_item.get_total_price()) if quantity > 0 else 0,
            'total_items': total_items,
            'sub_total': float(sub_total),
            'delivery_fee': float(total_delivery_fee),
            'tax_amount': float(tax_amount),
            'total_price': float(total_price)
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Error updating cart'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def remove_from_cart(request):
    """Remove item from cart (auth + guest)"""
    try:
        data = json.loads(request.body)
        cart_item_id = data.get('cart_item_id')

        user = request.user if request.user.is_authenticated else None
        session_key = None if user else get_session_key(request)

        try:
            cart_item = Cart.objects.get(id=cart_item_id, user=user, session_key=session_key)
            item_name = cart_item.menu_item.name
            cart_item.delete()
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Cart item not found'}, status=404)

        # Get updated cart totals
        cart_items = Cart.objects.filter(user=user) if user else Cart.objects.filter(session_key=session_key)
        
        # GROUP BY RESTAURANT and calculate delivery fee
        restaurant_groups = {}
        for item in cart_items:
            restaurant = item.menu_item.restaurant
            if restaurant not in restaurant_groups:
                restaurant_groups[restaurant] = []
            restaurant_groups[restaurant].append(item)

        total_delivery_fee = Decimal('0.00')
        for restaurant in restaurant_groups.keys():
            zone = restaurant.delivery_zones.first()
            if zone:
                total_delivery_fee += zone.delivery_fee
        
        total_items = sum(item.quantity for item in cart_items)
        sub_total = sum(item.get_total_price() for item in cart_items)
        tax_obj = TaxRate.objects.first()
        tax_rate = tax_obj.tax if tax_obj else Decimal('0.00')
        tax_amount = (sub_total + total_delivery_fee) * (tax_rate / Decimal('100'))
        total_price = sub_total + total_delivery_fee + tax_amount


        return JsonResponse({
            'success': True,
            'message': f'{item_name} removed from cart',
            'cart_count': total_items,
            'total_price': float(total_price)
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Error removing from cart'}, status=500)




# ===================
# Checkout
# ===================
def checkout(request):
    """Handle checkout process and create orders for both authenticated and guest users"""
    
    # Get cart items for authenticated or guest user
    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(user=request.user).select_related(
            'menu_item', 'menu_item__restaurant'
        ).prefetch_related('options')
        session_key = None
    else:
        # Guest user - use session key
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        cart_items = Cart.objects.filter(
            user__isnull=True,
            session_key=session_key
        ).select_related(
            'menu_item', 'menu_item__restaurant'
        ).prefetch_related('options')

    if not cart_items.exists():
        messages.error(request, "Your cart is empty. Please add items to proceed.")
        return redirect('all_collections')

    tax_obj = TaxRate.objects.first()
    tax_rate = tax_obj.tax if tax_obj else Decimal('0.00')

    coupon_code = request.session.get('coupon_code')
    coupon = None
    discount = Decimal('0.00')

    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            # Pass None for user if anonymous
            user_for_coupon = request.user if request.user.is_authenticated else None
            is_valid, message = coupon.is_valid(user=user_for_coupon, cart_items=list(cart_items))
            if not is_valid:
                request.session.pop('coupon_code', None)
                coupon = None
                messages.warning(request, message)
        except Coupon.DoesNotExist:
            request.session.pop('coupon_code', None)

    if request.method == "POST":
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone')
        full_name = request.POST.get('full_name')
        address = request.POST.get('address')
        city = request.POST.get('city')
        province = request.POST.get('province')
        postal_code = request.POST.get('postal_code', '')
        payment_method = request.POST.get('payment_method')

        if not all([email, phone, full_name, address, city, province, payment_method]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'website/pages/checkout.html', {
                'cart_items': cart_items,
                'coupon': coupon,
            })

        valid_provinces = [choice[0] for choice in Order.PROVINCE_CHOICES]
        if province not in valid_provinces:
            messages.error(request, "Please select a valid province.")
            return render(request, 'website/pages/checkout.html', {'cart_items': cart_items, 'coupon': coupon})

        valid_payment_methods = [choice[0] for choice in Order.PAYMENT_CHOICES]
        if payment_method not in valid_payment_methods:
            messages.error(request, "Please select a valid payment method.")
            return render(request, 'website/pages/checkout.html', {'cart_items': cart_items, 'coupon': coupon})

        # Group cart items by restaurant
        restaurant_items = {}
        for item in cart_items:
            restaurant = item.menu_item.restaurant
            restaurant_items.setdefault(restaurant, []).append(item)

        created_orders = []

        for restaurant, items in restaurant_items.items():
            subtotal = sum(item.get_total_price() for item in items)
            
            # Get delivery fee from first zone
            delivery_fee = Decimal('0.00')
            zone = restaurant.delivery_zones.first()
            if zone:
                delivery_fee = zone.delivery_fee
            
            tax_amount = (subtotal + delivery_fee) * (tax_rate / Decimal('100'))
            tax_amount = tax_amount.quantize(Decimal('0.01'))

            restaurant_discount = Decimal('0.00')
            if coupon:
                user_for_coupon = request.user if request.user.is_authenticated else None
                is_valid, message = coupon.is_valid(user=user_for_coupon, cart_items=items)
                if is_valid:
                    restaurant_discount = coupon.get_discount_amount(subtotal)
                else:
                    messages.warning(request, f"Coupon not valid for restaurant {restaurant.restaurant_name}.")

            total = max(subtotal + delivery_fee + tax_amount - restaurant_discount, Decimal('0.00'))
            total = total.quantize(Decimal('0.01'))

            # Calculate estimated delivery date
            prep_times = [item.menu_item.prep_time for item in items if item.menu_item.prep_time]
            max_prep_time = max(prep_times) if prep_times else 15
            estimated_delivery_date = timezone.now() + timedelta(minutes=max_prep_time + (zone.delivery_time_max if zone else 30))

            # Create Order - user can be None for guests (your model allows this)
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                email=email,
                phone=phone,
                full_name=full_name,
                address=address,
                city=city,
                province=province,
                postal_code=postal_code,
                payment_method=payment_method,
                payment_status='unpaid',
                subtotal=subtotal,
                shipping_cost=delivery_fee,
                tax_percentage=tax_rate,
                tax_amount=tax_amount,
                discount=restaurant_discount,
                total=total,
                coupon=coupon,
                status='received',
                estimated_delivery_date=estimated_delivery_date.date(),
                created_at=timezone.now(),
            )
            created_orders.append(order)

            # Create Order Items
            for item in items:
                order_item = OrderItem.objects.create(
                    order=order,
                    menu_item=item.menu_item,
                    quantity=item.quantity,
                    price=item.get_item_price(),
                    special_instructions=item.special_instructions,
                )
                order_item.options.set(item.options.all())

            # Record coupon usage (only for authenticated users since CouponUsage requires user)
            if coupon and restaurant_discount > 0 and request.user.is_authenticated:
                CouponUsage.objects.create(
                    user=request.user,
                    coupon=coupon,
                    order=order,
                    used_at=timezone.now(),
                )

        # Update coupon usage count only for authenticated users
        if coupon and discount > 0 and request.user.is_authenticated:
            coupon.used_count += 1
            coupon.save()

        # Clear cart - handle both auth and guest
        if request.user.is_authenticated:
            cart_items.delete()
        else:
            # For guest, delete only items with current session_key
            Cart.objects.filter(session_key=session_key).delete()
        
        request.session.pop('coupon_code', None)

        messages.success(request, f"{len(created_orders)} order(s) placed successfully!")
        
        # For guests, you might want to store order IDs in session for reference
        if not request.user.is_authenticated:
            request.session['last_order_id'] = created_orders[0].id
        
        return redirect('order_confirmation', order_id=created_orders[0].id)

    # --- GET Request ---
    subtotal = sum(item.get_total_price() for item in cart_items)

    # GROUP BY RESTAURANT AND CALCULATE DELIVERY FEE
    restaurant_groups = {}
    for item in cart_items:
        restaurant = item.menu_item.restaurant
        if restaurant not in restaurant_groups:
            restaurant_groups[restaurant] = []
        restaurant_groups[restaurant].append(item)

    delivery_breakdown = {}
    total_delivery_fee = Decimal('0.00')
    for restaurant, items in restaurant_groups.items():
        zone = restaurant.delivery_zones.first()
        delivery_fee = zone.delivery_fee if zone else Decimal('0.00')
        delivery_breakdown[restaurant.restaurant_name] = delivery_fee
        total_delivery_fee += delivery_fee

    tax_amount = (subtotal + total_delivery_fee) * (tax_rate / Decimal('100'))
    tax_amount = tax_amount.quantize(Decimal('0.01'))

    if coupon:
        discount = coupon.get_discount_amount(subtotal)

    total = subtotal + total_delivery_fee + tax_amount - discount
    total = total.quantize(Decimal('0.01'))

    for item in cart_items:
        item.options_list = list(item.options.all())
        item.unit_price = item.get_item_price()
        item.line_total = item.get_total_price()

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': total_delivery_fee,
        'delivery_breakdown': delivery_breakdown,
        'tax_rate': tax_rate,
        'tax': tax_amount,
        'discount': discount,
        'total': total,
        'coupon': coupon,
    }

    return render(request, 'website/pages/checkout.html', context)


@login_required
def apply_coupon(request):
    """Apply or remove a coupon code via AJAX"""
    coupon_code = request.POST.get('coupon_code', '').strip()
    action = request.POST.get('action', 'apply')

    if action == 'remove':
        request.session.pop('coupon_code', None)
        return JsonResponse({'success': True, 'message': 'Coupon removed successfully!'})

    try:
        coupon = Coupon.objects.get(code=coupon_code)
        cart_items = Cart.objects.filter(user=request.user).select_related('menu_item').prefetch_related('options')

        is_valid, message = coupon.is_valid(user=request.user, cart_items=cart_items)
        if not is_valid:
            return JsonResponse({'success': False, 'message': message}, status=400)

        request.session['coupon_code'] = coupon_code
        return JsonResponse({'success': True, 'message': f'Coupon "{coupon_code}" applied successfully!'})

    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid coupon code.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=400)


@login_required
def order_confirmation(request, order_id):
    """Display order confirmation - show all orders from same checkout session"""
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    
    first_order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Get all orders from same session (within 5 minutes)
    time_threshold = first_order.created_at + timedelta(minutes=5)
    orders = Order.objects.filter(
        user=request.user,
        created_at__gte=first_order.created_at,
        created_at__lte=time_threshold
    ).order_by('created_at')
    
    # Get all invoices
    invoices = Invoice.objects.filter(order__in=orders)
    
    # Build delivery breakdown 
    delivery_breakdown = {}
    for invoice in invoices:
        if invoice.restaurant:
            restaurant_name = invoice.restaurant.restaurant_name
        else:
            restaurant_name = "Platform Delivery"
        delivery_breakdown[restaurant_name] = invoice.shipping_cost
    
    # CALCULATE TOTALS FROM ALL ORDERS
    total_subtotal = sum(Decimal(str(o.subtotal)) for o in orders)
    total_shipping = sum(Decimal(str(o.shipping_cost)) for o in orders)
    total_tax = sum(Decimal(str(o.tax_amount)) for o in orders)
    total_discount = sum(Decimal(str(o.discount)) for o in orders)
    grand_total = sum(Decimal(str(o.total)) for o in orders)
    
    return render(request, 'website/pages/order_confirmation.html', {
        'order': first_order,
        'orders': orders,
        'invoices': invoices,
        'delivery_breakdown': delivery_breakdown,
        'total_subtotal': total_subtotal,
        'total_delivery_fee': total_shipping,
        'total_tax': total_tax,
        'total_discount': total_discount,
        'grand_total': grand_total,
    })



def menu_item_details(request, slug):
    try:
        menu_item = MenuItem.objects.select_related('restaurant')\
                    .prefetch_related('images', 'options', 'reviews')\
                    .get(slug=slug, is_available=True)

        menu_item.views_count += 1
        menu_item.save(update_fields=['views_count'])

        # Recommended menu items from same restaurant
        recommended_items = menu_item.restaurant.menu_items.filter(is_available=True).exclude(id=menu_item.id)[:12]

        reviews = menu_item.reviews.select_related('user').order_by('-created_at')[:10]

        context = {
            'menu_item': menu_item,
            'restaurant': menu_item.restaurant,
            'recommended_items': recommended_items,
            'reviews': reviews,
            'banners': Banner.objects.filter(is_active=True, page="menu"),
        }

        return render(request, 'website/pages/menu_item_details.html', context)

    except MenuItem.DoesNotExist:
        messages.error(request, 'Menu item not found')
        return redirect('home')





def login_page(request):
    if request.user.is_authenticated:
        role_obj = getattr(request.user, 'role', None)
        if role_obj.role == 'admin':
            return redirect('admin_dashboard')
        elif role_obj.role == 'staff':
            return redirect('staff_dashboard')
        elif role_obj.role == 'customer':
            return redirect('customer_profile')
        elif role_obj.role == 'restaurant':
            return redirect('restaurant_dashboard')
        elif role_obj.role == 'delivery':
            return redirect('delivery_dashboard')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email=email, is_active=True)
            # Check user role before password check
            role_obj = getattr(user, 'role', None)
            if role_obj and role_obj.role == 'customer':
                messages.error(request, 'Please log in via the e-commerce platform.')
                # Redirect to your e-commerce login page (replace with your actual URL)
                return redirect('http://nfc.alsamainternational.com/login/')
            if user.check_password(password):
                auth_login(request, user)
                messages.success(request, 'Login Successful')
                role_obj = getattr(request.user, 'role', None)
                if role_obj:
                    if role_obj.role == 'admin':
                        return redirect('admin_dashboard')
                    elif role_obj.role == 'staff':
                        return redirect('staff_dashboard')
                    elif role_obj.role == 'customer':
                        return redirect('customer_profile')
                    elif role_obj.role == 'restaurant':
                        return redirect('restaurant_dashboard')
                    elif role_obj.role == 'delivery':
                        return redirect('delivery_dashboard')
                # Default redirect if no role found
                return redirect('home_page')
            else:
                messages.error(request, 'Invalid Username and Password')
                return redirect('login_page')
        except User.DoesNotExist:
            messages.error(request, 'Invalid Username and Password')
            return redirect('login_page')
    return render(request, 'website/pages/login.html')


def signup_page(request):
    if request.method == "POST":
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email', '').strip()
         

            if User.objects.filter(email=email, is_active=True).exists():
                messages.error(request, 'User already exists')
                return redirect('signup_page')

            if User.objects.filter(email=email, is_active=False).exists():
                user = User.objects.get(email=email)
                user.first_name = first_name
                user.last_name = last_name
                user.save()
            else:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False
                )

            otp = str(random.randint(100000, 999999))
            otp_obj, _ = OTPVerification.objects.get_or_create(user=user)
            otp_obj.otp_code = otp
            otp_obj.save()

            try:
                send_mail(
                    subject="Your Hello Bajar OTP Verification Code",
                    message=f"Hello {first_name},\n\nYour OTP code is: {otp}",
                    from_email="hellobajar@gmail.com",
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as mail_error:
                messages.error(request, f"Error sending OTP email: {mail_error}")
                return redirect('signup_page')

            request.session['user_email'] = email
            messages.info(request, "OTP has been sent to your email.")
            return redirect('verify_otp_page')

        except Exception as e:
            messages.error(request, f"Something went wrong: {e}")
            return redirect('signup_page')

    return render(request, 'website/pages/signup.html')




def forget_password(request):
    if request.method == "POST":
        email=request.POST.get('email', '').strip().lower()
        try:
            user=User.objects.get(email=email,is_active=True)
        except User.DoesNotExist:
            messages.error(request,'No account found with that email')
            return render(request,'website/pages/forget.html')
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
        request.session['user_email']=email
        messages.success(request,'OTP sent to your email')
        return redirect('verify_otp_page')
    return render(request,'website/pages/forget.html')


def set_password_view(request):

    if request.method  == "POST":
        new_password=request.POST.get('new_password')
        try:
            user=User.objects.get(email=request.user.email,is_active=True)
            user.set_password(new_password)
            user.save()
            messages.success(request,'Password changed successfully. Please Login')
            return redirect('login_page')
        except User.DoesNotExist:
            messages.error(request,'User not found')
            return redirect('forget_password')
    return render(request,'website/pages/set_password.html')



def verify_otp_page(request):
    email = request.session.get('user_email')
    try:
        user = User.objects.get(email=email)
        otp_obj = OTPVerification.objects.get(user=user)
    except (User.DoesNotExist, OTPVerification.DoesNotExist):
        messages.error(request, "Invalid request.")
        return redirect('login_page')

    if request.method == "POST":
        entered_otp = request.POST.get('otp', '').strip()

        if entered_otp == otp_obj.otp_code:
            if not user.is_active:
                user.is_active = True
                user.save()
                if Restaurant.objects.filter(user=user).exists():
                    UserRole.objects.get_or_create(role="restaurant",user=user)
                else:
                    UserRole.objects.get_or_create(role="customer",user=user)
                    
               
                UserProfile.objects.get_or_create(user=user)
                otp_obj.delete()
                del request.session['user_email']
                auth_login(request, user)
                messages.success(request, "Your account has been verified successfully!")
                return redirect('set_password')
            elif user.is_active:
                otp_obj.delete()
                del request.session['user_email']
                auth_login(request, user)
                messages.success(request, "Otp verified successfully! Please Reset New Password")
                return redirect('set_password')
                
            
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'website/pages/otp.html', {'email': email})


def logout_view(request):
    auth_logout(request)
    messages.success(request,'Logout Successfull')
    return redirect('login_page')



def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        Contact.objects.create(
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                message=message_text
            )
        messages.success(request, "Your message has been sent successfully!")
        return redirect('contact')
       

    return render(request, 'website/pages/contact.html')

    


# =============================
#  Customer Dashboard
# =============================

@login_required
def customer_profile(request):
    role_obj = getattr(request.user, 'role', None)
    if role_obj:
        if role_obj.role == 'admin':
            return redirect('admin_dashboard')
        if role_obj.role == 'staff':
            return redirect('staff_dashboard')
    return render(request, 'website/pages/profile.html')


@login_required
def edit_profile(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()

        profile.phone = request.POST.get('phone', '').strip()
        profile.address = request.POST.get('address', '').strip()
        profile.city = request.POST.get('city', '').strip()
        profile.province = request.POST.get('province', '').strip()

        if request.FILES.get('avatar'):
            profile.avatar = request.FILES['avatar']

        user.save()
        profile.save()

        return redirect('customer_profile') 

    return render(request, 'website/pages/edit_profile.html', {
        'profile': profile,
    })
    
    

@login_required
def customer_orders(request):
        user=request.user
        orders_list = Order.objects.filter(user=user).order_by('-created_at')
        total_orders=orders_list.count()
        
       
        paginator = Paginator(orders_list, 10) 
        
        page_number = request.GET.get('page')
        orders = paginator.get_page(page_number)
        
        return render(request, 'website/pages/orders.html', {
            'orders': orders,
            'total_orders':total_orders,
            
        })


@login_required
def customer_order_detail(request, order_number):

    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    coupon_used = order.coupon if order.coupon else None

    return render(request, 'website/pages/order_detail.html', {
        'order': order,
        'order_items': order_items,
        'coupon_used': coupon_used,
       
    })


# =====================
#  Invoice
# ====================

@login_required
def customer_invoices(request):
    invoice_list=Invoice.objects.filter(customer=request.user).order_by('-created_at')
    paginator=Paginator(invoice_list,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)
    return render(request,'website/pages/invoices.html',{'page_obj':page_obj})


@login_required
def customer_invoice_detail(request, invoice_number):
    invoice = get_object_or_404(Invoice, invoice_number=invoice_number, customer=request.user)
    return render(request, 'website/pages/invoice_detail.html', {'invoice': invoice})


@login_required
def write_menu_review(request, menu_item_id):
    menu_item = get_object_or_404(MenuItem, id=menu_item_id)
    order_id = request.GET.get('order')
    order = Order.objects.filter(id=order_id).first()

    existing_review = MenuItemReview.objects.filter(menu_item=menu_item, user=request.user).first()

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Please select a valid rating between 1 and 5 stars.")
            return render(request, 'website/pages/write_review.html', {
                'menu_item': menu_item, 'comment': comment, 'rating': rating
            })

        if existing_review:
            existing_review.rating = rating
            existing_review.comment = comment
            existing_review.save()
            messages.success(request, "Your review has been updated!")
        else:
            MenuItemReview.objects.create(menu_item=menu_item, user=request.user, rating=rating, comment=comment)
            messages.success(request, "Thank you for your review!")

        return redirect('customer_order_detail', order_number=order.order_number) if order else redirect('menu_item_details', slug=menu_item.slug)

    existing_reviews = MenuItemReview.objects.filter(menu_item=menu_item).exclude(user=request.user).order_by('-created_at')[:5]

    return render(request, 'website/pages/write_review.html', {
        'menu_item': menu_item,
        'order_number': order.order_number if order else None,
        'existing_review': existing_review,
        'existing_reviews': existing_reviews,
        'comment': existing_review.comment if existing_review else '',
        'rating': existing_review.rating if existing_review else None,
    })




@csrf_exempt
def login_with_token(request):
    if request.method == "POST":
        token = request.POST.get('token')
        
        if not token:
            return redirect('login_page')
        try:
            token_obj = AccessToken(token)
            email = token_obj.get('email')
            
            if not email:
                print(" No email ")
                return redirect('login_page')
            
            # GET OR CREATE user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': token_obj.get('first_name', ''),
                    'last_name': token_obj.get('last_name', ''),
                    'is_active': True,
                }
            )
            
            # If user was just created, ensure they have profile/role
            if created:
                UserProfile.objects.get_or_create(user=user)
                UserRole.objects.get_or_create(user=user, defaults={'role': 'customer'})
                print(f" New user created and logged in: {email}")
            else:
                print(f" Existing user logged in: {email}")
            
            auth_login(request, user)
            return redirect('home')
            
        except Exception as e:
            print(f" Token validation error: {str(e)}")
            return redirect('login_page')
    
    return render(request, 'website/pages/login_with_token.html')