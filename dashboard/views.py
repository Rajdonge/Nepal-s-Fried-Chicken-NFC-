from itertools import product
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, F, Count
from django.utils import timezone
from decimal import Decimal
from django.db import IntegrityError
from datetime import timedelta
from django.db.models.functions import TruncDate
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib import messages
from .models import (
    DeliveryAssignment, DeliveryPerson, StaffProfile, UserRole, Restaurant, 
    CuisineType, MenuSection, MenuItem, MenuItemImage, MenuItemOption, Order, 
    OrderItem, Invoice, RestaurantReview, Coupon, Organization, Newsletter, 
    Contact, FoodTag, Notification, Slider, Banner, RestaurantCommission, 
    RestaurantPayoutRequest, RestaurantWallet, TaxRate, DeliveryZone,
    RestaurantTiming, MenuItemReview, Review
)
import datetime
from django.http import HttpResponseForbidden
from functools import wraps
import json
import os
from django.conf import settings

# Helper decorator to check admin access
def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'role') or not request.user.role.is_admin():
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper




def staff_or_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        try:
            role_obj = request.user.role
            role = role_obj.role
        except Exception:
            return HttpResponseForbidden()
        if role == 'admin':
            return view_func(request, *args, **kwargs)
        if role == 'staff':
            try:
                staff = request.user.staff_profile
            except StaffProfile.DoesNotExist:
                return HttpResponseForbidden()
            request.staff_district = staff.district.strip()
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden()
    return _wrapped
    
# ===================
# Admin Dashboard
# ===================
# Admin Dashboard (Last 30 Days)
@admin_required
def admin_dashboard(request):
    # Date range
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)

    # Users
    total_users = User.objects.count()
    customers_count = UserRole.objects.filter(role='customer').count()
    admins_count = UserRole.objects.filter(role='admin').count()

    # Restaurants (use Restaurant count as source of truth)
    total_restaurants = Restaurant.objects.count()
    restaurants_count = total_restaurants  # Keep for consistency in view
    verified_restaurants = Restaurant.objects.filter(verification_status='verified').count()
    pending_restaurants = Restaurant.objects.filter(verification_status='pending').count()

    # Menu Items
    total_menu_items = MenuItem.objects.count()
    available_menu_items = MenuItem.objects.filter(is_available=True).count()
    unavailable_menu_items = MenuItem.objects.filter(is_available=False).count()

    # Orders
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    total_revenue = Order.objects.filter(payment_status='paid').aggregate(Sum('total'))['total__sum'] or 0

    # Last 30 days analytics
    recent_orders = Order.objects.filter(payment_status='paid', created_at__date__gte=last_30_days)
    recent_menu_items = MenuItem.objects.filter(created_at__date__gte=last_30_days)

    # Daily revenue & orders
    daily_orders = (recent_orders
                    .annotate(date=TruncDate('created_at'))
                    .values('date')
                    .annotate(total_orders=Count('id'), revenue=Sum('total'))
                    .order_by('date'))
    
    revenue_labels = [item['date'].strftime('%Y-%m-%d') for item in daily_orders]
    revenue_data = [float(item['revenue'] or 0) for item in daily_orders]
    orders_data = [item['total_orders'] for item in daily_orders]

    # Daily new menu items
    daily_menu_items = (recent_menu_items
                      .annotate(date=TruncDate('created_at'))
                      .values('date')
                      .annotate(new_items=Count('id'))
                      .order_by('date'))
    menu_item_labels = [item['date'].strftime('%Y-%m-%d') for item in daily_menu_items]
    new_menu_items_data = [item['new_items'] for item in daily_menu_items]

    # Content / Others
    active_sliders = Slider.objects.filter(is_active=True).count()
    active_banners = Banner.objects.filter(is_active=True).count()
    active_cuisines = CuisineType.objects.filter(is_featured=True).count()
    total_reviews = MenuItemReview.objects.count() + RestaurantReview.objects.count()
    unread_contacts = Contact.objects.filter(is_read=False).count()
    newsletter_subscribers = Newsletter.objects.filter(is_active=True).count()
    unread_notifications = Notification.objects.filter(is_read=False).count()

    context = {
        'total_users': total_users,
        'customers_count': customers_count,
        'restaurants_count': restaurants_count,
        'admins_count': admins_count,
        'total_restaurants': total_restaurants,
        'verified_restaurants': verified_restaurants,
        'pending_restaurants': pending_restaurants,
        'total_menu_items': total_menu_items,
        'available_menu_items': available_menu_items,
        'unavailable_menu_items': unavailable_menu_items,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'total_revenue': total_revenue,
        'active_sliders': active_sliders,
        'active_banners': active_banners,
        'active_cuisines': active_cuisines,
        'total_reviews': total_reviews,
        'unread_contacts': unread_contacts,
        'newsletter_subscribers': newsletter_subscribers,
        'unread_notifications': unread_notifications,
        'revenue_labels': revenue_labels,
        'revenue_data': revenue_data,
        'orders_data': orders_data,
        'menu_item_labels': menu_item_labels,
        'new_menu_items_data': new_menu_items_data,
    }

    return render(request, 'dashboard/pages/admin_dashboard.html', context)

# ===================
# User Management
# ===================
# User Management
@admin_required
def admin_users_list(request):
    search = request.GET.get('search', '')
    role = request.GET.get('role', '')
    users = User.objects.all().select_related('role').order_by('-date_joined')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search)
        )

    if role in ['customer', 'vendor', 'admin','staff']:
        users = users.filter(role__role=role)

    return render(request, 'dashboard/pages/users/users_list.html', {
        'users': users,
    })


#----Staffs Management by Admin----#
@admin_required
def admin_staff_list(request):
    staffs = User.objects.filter(role__role='staff').select_related('role').order_by('-date_joined')
    # prefetch staff_profile to avoid N+1
    staffs = staffs.prefetch_related('staff_profile')
    return render(request, 'dashboard/pages/staffs/staffs_list.html', {
        'staffs': staffs,
    })

@admin_required
def admin_staff_add(request):
    form_data = {}
    
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        phone = request.POST.get('phone', '').strip()
        province = request.POST.get('province', '').strip()
        district = request.POST.get('district', '').strip()
        citizenship = request.POST.get('citizenship', '').strip()
        father_name = request.POST.get('father_name', '').strip()
        grandfather_name = request.POST.get('grandfather_name', '').strip()
        
        photo_base64 = request.POST.get('photo_base64', '')
        citizenship_front_base64 = request.POST.get('citizenship_front_base64', '')
        citizenship_back_base64 = request.POST.get('citizenship_back_base64', '')
        
        citizenship_front = request.FILES.get('citizenship_front')
        citizenship_back = request.FILES.get('citizenship_back')
        photo = request.FILES.get('photo')

        form_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'district': district,
            'citizenship': citizenship,
            'grandfather_name': grandfather_name,
            'father_name': father_name,
            'province': province,
            'photo_base64': photo_base64,
            'citizenship_front_base64': citizenship_front_base64,
            'citizenship_back_base64': citizenship_back_base64,
        }

        districts = sorted(set(
            list(Restaurant.objects.values_list('city', flat=True).distinct()) +
            list(Order.objects.exclude(city__isnull=True).exclude(city__exact='').values_list('city', flat=True).distinct()) +
            list(StaffProfile.objects.values_list('district', flat=True).distinct())
        ))
        districts = [d for d in districts if d]

        # Validation - All required fields
        if not (first_name and last_name and email and password and confirm_password and phone and district and citizenship and grandfather_name):
            messages.error(request, 'All fields are required.')
            return render(request, 'dashboard/pages/staffs/add_staff.html', {
                'districts': districts,
                'form_data': form_data,
            })

        # Validation - Passwords match 
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'dashboard/pages/staffs/add_staff.html', {
                'districts': districts,
                'form_data': form_data,
            })
        
        # Validation - Password length
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'dashboard/pages/staffs/add_staff.html', {
                'districts': districts,
                'form_data': form_data,
            })
        
        # Validation - Email unique
        if User.objects.filter(email=email).exists():
            messages.error(request, 'User with that email already exists.')
            return render(request, 'dashboard/pages/staffs/add_staff.html', {
                'districts': districts,
                'form_data': form_data,
            })

        # Validate files exist
        if not photo and not photo_base64:
            messages.error(request, 'Photo is required.')
            return render(request, 'dashboard/pages/staffs/add_staff.html', {
                'districts': districts,
                'form_data': form_data,
            })

        if not citizenship_front and not citizenship_front_base64:
            messages.error(request, 'Citizenship Front is required.')
            return render(request, 'dashboard/pages/staffs/add_staff.html', {
                'districts': districts,
                'form_data': form_data,
            })

        if not citizenship_back and not citizenship_back_base64:
            messages.error(request, 'Citizenship Back is required.')
            return render(request, 'dashboard/pages/staffs/add_staff.html', {
                'districts': districts,
                'form_data': form_data,
            })

        # All validations passed - Create user and staff profile
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )

        UserRole.objects.create(user=user, role='staff')
        
        StaffProfile.objects.create(
            user=user, 
            district=district,
            phone=phone,
            citizenship=citizenship,
            citizenship_front=citizenship_front,
            citizenship_back=citizenship_back,
            photo=photo,
            grandfather_name=grandfather_name,
            father_name=father_name
        )

        messages.success(request, 'Staff user created successfully.')
        return redirect('admin_staff_list')
    
    districts = sorted(set(
        list(Restaurant.objects.values_list('city', flat=True).distinct()) +
        list(Order.objects.exclude(city__isnull=True).exclude(city__exact='').values_list('city', flat=True).distinct()) +
        list(StaffProfile.objects.values_list('district', flat=True).distinct())
    ))
    districts = [d for d in districts if d]

    return render(request, 'dashboard/pages/staffs/add_staff.html', {
        'districts': districts,
        'form_data': form_data,
    })

@admin_required
def admin_staff_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    
    if not hasattr(user, 'role') or user.role.role != 'staff':
        messages.error(request, 'User is not a staff member.')
        return redirect('admin_staff_list')

    staff_profile = user.staff_profile if hasattr(user, 'staff_profile') else None
    form_data = {}

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        district = request.POST.get('district', '').strip()
        citizenship = request.POST.get('citizenship', '').strip()
        grandfather_name = request.POST.get('grandfather_name', '').strip()
        father_name = request.POST.get('father_name', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        photo_base64 = request.POST.get('photo_base64', '')
        citizenship_front_base64 = request.POST.get('citizenship_front_base64', '')
        citizenship_back_base64 = request.POST.get('citizenship_back_base64', '')
        
        citizenship_front = request.FILES.get('citizenship_front')
        citizenship_back = request.FILES.get('citizenship_back')
        photo = request.FILES.get('photo')
        province = request.POST.get('province', '').strip()

        form_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'district': district,
            'citizenship': citizenship,
            'grandfather_name': grandfather_name,
            'father_name': father_name,
            'province': province,
            'photo_base64': photo_base64,
            'citizenship_front_base64': citizenship_front_base64,
            'citizenship_back_base64': citizenship_back_base64,
        }

        districts = sorted(set(
            list(Restaurant.objects.values_list('city', flat=True).distinct()) +
            list(Order.objects.exclude(city__isnull=True).exclude(city__exact='').values_list('city', flat=True).distinct()) +
            list(StaffProfile.objects.values_list('district', flat=True).distinct())
        ))
        districts = [d for d in districts if d]

        # Validate email not in use
        if email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
            messages.error(request, 'Email already in use.')
            return render(request, 'dashboard/pages/staffs/edit_staff.html', {
                'user': user,
                'staff_profile': staff_profile,
                'districts': districts,
                'form_data': form_data,
            })

        # Validate password if provided
        if password or confirm_password:
            if password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'dashboard/pages/staffs/edit_staff.html', {
                    'user': user,
                    'staff_profile': staff_profile,
                    'districts': districts,
                    'form_data': form_data,
                })

            if len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return render(request, 'dashboard/pages/staffs/edit_staff.html', {
                    'user': user,
                    'staff_profile': staff_profile,
                    'districts': districts,
                    'form_data': form_data,
                })

        # Update user
        user.first_name = first_name
        user.last_name = last_name
        if email:
            user.email = email
            user.username = email
        
        # Update password if provided
        if password:
            user.set_password(password)
        
        user.save()

        # Update staff profile
        if staff_profile:
            staff_profile.district = district
            staff_profile.phone = phone
            staff_profile.citizenship = citizenship
            staff_profile.grandfather_name = grandfather_name
            staff_profile.father_name = father_name
            if citizenship_front:
                staff_profile.citizenship_front = citizenship_front
            if citizenship_back:
                staff_profile.citizenship_back = citizenship_back
            if photo:
                staff_profile.photo = photo
            
            staff_profile.save()
        else:
            StaffProfile.objects.create(
                user=user,
                district=district,
                phone=phone,
                citizenship=citizenship,
                citizenship_front=citizenship_front,
                citizenship_back=citizenship_back,
                photo=photo,
                grandfather_name=grandfather_name,
                father_name=father_name
                
            )

        messages.success(request, 'Staff updated successfully.')
        return redirect('admin_staff_list')
    
    districts = sorted(set(
        list(Restaurant.objects.values_list('city', flat=True).distinct()) +
        list(Order.objects.exclude(city__isnull=True).exclude(city__exact='').values_list('city', flat=True).distinct()) +
        list(StaffProfile.objects.values_list('district', flat=True).distinct())
    ))
    districts = [d for d in districts if d]

    return render(request, 'dashboard/pages/staffs/edit_staff.html', {
        'user': user,
        'staff_profile': staff_profile,
        'districts': districts,
        'form_data': form_data,
    })
# @admin_required
# def admin_user_add(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         role = request.POST.get('role')
#         user = User.objects.create_user(username=username, email=email, password=password)
#         UserRole.objects.create(user=user, role=role)
#         return redirect('admin_users_list')
#     return render(request, 'dashboard/pages/users/user_add.html')

@admin_required
def admin_user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email', '').strip().lower()
        user.first_name=request.POST.get('first_name')
        user.last_name=request.POST.get('last_name')
        user.save()      
        return redirect('admin_users_list')
    return render(request, 'dashboard/pages/users/edit_user.html', {'user': user})

@admin_required
def admin_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    
    if user.pk == request.user.pk:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('admin_users_list')
    
    # Check if user is a restaurant with incomplete orders
    try:
        restaurant = Restaurant.objects.get(user=user)
        incomplete_orders = Order.objects.filter(
            items__menu_item__restaurant=restaurant
        ).exclude(status='delivered').distinct()
        
        if incomplete_orders.exists():
            messages.error(request, f"Cannot delete restaurant user '{user.username}'. They have {incomplete_orders.count()} incomplete order(s).")
            return redirect('admin_users_list')
    except Restaurant.DoesNotExist:
        pass
    
    # Check if user is a customer with incomplete orders
    incomplete_orders = Order.objects.filter(
        user=user
    ).exclude(status='delivered').distinct()
    
    if incomplete_orders.exists():
        messages.error(request, f"Cannot delete customer user '{user.username}'. They have {incomplete_orders.count()} incomplete order(s).")
        return redirect('admin_users_list')
    
    messages.success(request, f'User {user.first_name} deleted successfully.')
    user.delete()
    return redirect('admin_users_list')

# Helper used inline (optional local helper)
def _orders_for_staff(orders_qs, request):
    staff_district = getattr(request, 'staff_district', None)
    if staff_district:
        return orders_qs.filter(items__menu_item__restaurant__city__iexact=staff_district).distinct()
    return orders_qs

#===================
# staff Dashboard Management
# ===================
@staff_or_admin_required
def staff_dashboard(request):
    # Get staff's assigned district
    district = getattr(request, 'staff_district', '')
    
    if not district:
        context = {'district': district}
        return render(request, 'dashboard/staff/pages/staff_dashboard.html', context)
    
    # Date range for analytics
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    
    # ===== RESTAURANTS (In District) =====
    district_restaurants = Restaurant.objects.filter(city__iexact=district)
    total_restaurants = district_restaurants.count()
    verified_restaurants = district_restaurants.filter(verification_status='verified').count()
    pending_restaurants = district_restaurants.filter(verification_status='pending').count()
    
    # ===== MENU ITEMS (From District Restaurants) =====
    district_menu_items = MenuItem.objects.filter(restaurant__city__iexact=district)
    total_menu_items = district_menu_items.count()
    active_menu_items = district_menu_items.filter(is_available=True).count()
    
    # ===== ORDERS (From District Restaurants) =====
    district_orders = Order.objects.filter(items__menu_item__restaurant__city__iexact=district).distinct()
    total_orders = district_orders.count()
    pending_orders = district_orders.filter(status='pending').count()
    delivered_orders = district_orders.filter(status='delivered').count()
    total_revenue = district_orders.filter(payment_status='paid').aggregate(Sum('total'))['total__sum'] or 0
    
    # ===== LAST 30 DAYS ANALYTICS =====
    recent_orders = district_orders.filter(payment_status='paid', created_at__date__gte=last_30_days)
    recent_menu_items = district_menu_items.filter(created_at__date__gte=last_30_days)
    
    # Daily revenue & orders
    daily_orders = (recent_orders
                    .annotate(date=TruncDate('created_at'))
                    .values('date')
                    .annotate(total_orders=Count('id'), revenue=Sum('total'))
                    .order_by('date'))
    
    revenue_labels = [item['date'].strftime('%Y-%m-%d') for item in daily_orders]
    revenue_data = [float(item['revenue'] or 0) for item in daily_orders]
    orders_data = [item['total_orders'] for item in daily_orders]
    
    # Daily new menu items
    daily_menu_items = (recent_menu_items
                      .annotate(date=TruncDate('created_at'))
                      .values('date')
                      .annotate(new_items=Count('id'))
                      .order_by('date'))
    menu_item_labels = [item['date'].strftime('%Y-%m-%d') for item in daily_menu_items]
    new_menu_items_data = [item['new_items'] for item in daily_menu_items]
    
    context = {
        'district': district,
        'total_restaurants': total_restaurants,
        'verified_restaurants': verified_restaurants,
        'pending_restaurants': pending_restaurants,
        'total_menu_items': total_menu_items,
        'active_menu_items': active_menu_items,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'total_revenue': total_revenue,
        'revenue_labels': revenue_labels,
        'revenue_data': revenue_data,
        'orders_data': orders_data,
        'menu_item_labels': menu_item_labels,
        'new_menu_items_data': new_menu_items_data,
    }
    
    return render(request, 'dashboard/staff/pages/staff_dashboard.html', context)

@staff_or_admin_required
def staff_profile_view(request):
    # staff_or_admin_required sets request.staff_district for staff users
    staff_district = getattr(request, 'staff_district', None)
    return render(request, 'dashboard/staff/pages/staff_profile.html', {
        'user': request.user,
        'staff_district': staff_district,
    })


# ========================
#  Delivery Person Dashboard
# ========================

@login_required
def delivery_home(request):
    """Redirect to dashboard - just a landing page"""
    if not hasattr(request.user, 'delivery_person'):
        messages.error(request, 'Access denied. You are not a delivery person.')
        return redirect('admin_dashboard')
    return redirect('delivery_dashboard')


@login_required
def delivery_dashboard(request):
    """Main dashboard with stats"""
    if not hasattr(request.user, 'delivery_person'):
        return HttpResponseForbidden('Access denied.')
    
    delivery_person = request.user.delivery_person
    
    # Get all assignments for this person
    all_assignments = DeliveryAssignment.objects.filter(delivery_person=delivery_person)
    
    # Stats
    assigned = all_assignments.filter(status='assigned').count()
    picked_up = all_assignments.filter(status='picked_up').count()
    in_transit = all_assignments.filter(status='in_transit').count()
    delivered = all_assignments.filter(status='delivered').count()
    failed = all_assignments.filter(status='failed').count()
    
    # Recent assignments (last 10)
    recent = all_assignments[:10]
    
    context = {
        'delivery_person': delivery_person,
        'assigned': assigned,
        'picked_up': picked_up,
        'in_transit': in_transit,
        'delivered': delivered,
        'failed': failed,
        'total': all_assignments.count(),
        # 'success_rate': delivery_person.success_rate,
        'recent_assignments': recent,
    }
    
    return render(request, 'dashboard/delivery/pages/dashboard.html', context)


@login_required
def delivery_orders_list(request):
    """List all assigned orders for this delivery person"""
    if not hasattr(request.user, 'delivery_person'):
        return HttpResponseForbidden('Access denied.')
    
    delivery_person = request.user.delivery_person
    
    # Filter by status if provided
    status_filter = request.GET.get('status', '')
    assignments = DeliveryAssignment.objects.filter(delivery_person=delivery_person)
    
    if status_filter:
        assignments = assignments.filter(status=status_filter)
    
    context = {
        'assignments': assignments,
        'status_choices': DeliveryAssignment.STATUS_CHOICES,
        'selected_status': status_filter,
    }
    
    return render(request, 'dashboard/delivery/pages/orders_list.html', context)


@login_required
def delivery_order_detail(request, assignment_id):
    """View and update delivery assignment status"""
    if not hasattr(request.user, 'delivery_person'):
        return HttpResponseForbidden('Access denied.')
    
    delivery_person = request.user.delivery_person
    assignment = get_object_or_404(DeliveryAssignment, id=assignment_id, delivery_person=delivery_person)
    order = assignment.order
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        failure_reason = request.POST.get('failure_reason', '')
        
        delivery_photo = request.FILES.get('delivery_photo')

        
        # Validate status
        valid_statuses = [choice[0] for choice in DeliveryAssignment.STATUS_CHOICES]
        if new_status not in valid_statuses:
            messages.error(request, 'Invalid status')
            return redirect('delivery_order_detail', assignment_id=assignment.id)
        
        # Update assignment
        old_status = assignment.status
        assignment.status = new_status
        
        # Set timestamp only when transitioning to that status
        if new_status == 'picked_up' and assignment.picked_up_at is None:
            assignment.picked_up_at = timezone.now()
        elif new_status == 'in_transit' and assignment.in_transit_at is None:
            assignment.in_transit_at = timezone.now()
        elif new_status == 'delivered' and assignment.delivered_at is None:
            assignment.delivered_at = timezone.now()
        
        assignment.notes = notes
        if new_status == 'failed':
            assignment.failure_reason = failure_reason

        if delivery_photo:
            assignment.delivery_photo = delivery_photo
    
        
        assignment.save()
        
        messages.success(request, f'Order status updated to {assignment.get_status_display()}')
        return redirect('delivery_order_detail', assignment_id=assignment.id)
    
    context = {
        'assignment': assignment,
        'order': order,
        'status_choices': DeliveryAssignment.STATUS_CHOICES,
    }
    
    return render(request, 'dashboard/delivery/pages/order_detail.html', context)
@login_required
def delivery_profile(request):
    """Delivery person profile edit"""
    if not hasattr(request.user, 'delivery_person'):
        return HttpResponseForbidden('Access denied.')
    
    delivery_person = request.user.delivery_person
    
    if request.method == 'POST':
        delivery_person.phone = request.POST.get('phone', delivery_person.phone)
        delivery_person.address = request.POST.get('address', delivery_person.address)
        delivery_person.save()
        messages.success(request, 'Profile updated successfully')
        return redirect('delivery_profile')
    
    # Calculate performance stats from assignments
    all_assignments = DeliveryAssignment.objects.filter(delivery_person=delivery_person)
    total_deliveries = all_assignments.count()
    successful_deliveries = all_assignments.filter(status='delivered').count()
    failed_deliveries = all_assignments.filter(status='failed').count()
    
    context = {
        'delivery_person': delivery_person,
        'total_deliveries': total_deliveries,
        'successful_deliveries': successful_deliveries,
        'failed_deliveries': failed_deliveries,
    }
    
    return render(request, 'dashboard/delivery/pages/profile.html', context)


#admin delivery person management


# ========================
#  Delivery Person Management (Admin)
# ========================

@staff_or_admin_required
def admin_delivery_persons_list(request, **kwargs):
    """List delivery persons (staff scoped by district)"""
    staff_district = getattr(request, 'staff_district', None)
    search = request.GET.get('search', '')
    
    if staff_district:
        # Staff sees only delivery persons in their district
        delivery_persons = DeliveryPerson.objects.filter(district=staff_district)
    else:
        # Admin sees all delivery persons
        delivery_persons = DeliveryPerson.objects.all()
    
    # Search by name, email, or phone
    if search:
        delivery_persons = delivery_persons.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    context = {
        'delivery_persons': delivery_persons.order_by('-created_at'),
        'search': search,
        'page_title': 'Delivery Persons',
    }
    return render(request, 'dashboard/pages/delivery/delivery_persons_list.html', context)


@staff_or_admin_required
def admin_delivery_person_create(request, **kwargs):
    """Create delivery person (staff auto-scoped to their district)"""
    staff_district = getattr(request, 'staff_district', None)
    form_data = {}
    
    # Load all districts from nepal_provinces.json
    try:
        json_path = os.path.join(settings.BASE_DIR, 'static/data/nepal_provinces.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            nepal_data = json.load(f)
        
        # Extract all districts from all provinces
        districts = []
        for province in nepal_data:
            districts.extend(province.get('districts', []))
        districts = sorted(list(set(districts)))
    except:
        districts = []
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        district = request.POST.get('district', '').strip() if not staff_district else staff_district
        
        form_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'address': address,
            'district': district,
        }
        
        # Validation - UPDATE ALL RENDER CALLS:
        if not first_name or not last_name:
            messages.error(request, 'First name and last name are required.')
            return render(request, 'dashboard/pages/delivery/create_delivery_person.html', {
                'form_data': form_data,
                'is_staff': staff_district is not None,
                'districts': districts,
                'staff_district': staff_district,
            })
        
        if not email:
            messages.error(request, 'Email is required.')
            return render(request, 'dashboard/pages/delivery/create_delivery_person.html', {
                'form_data': form_data,
                'is_staff': staff_district is not None,
                'districts': districts,
                'staff_district': staff_district,
            })
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'dashboard/pages/delivery/create_delivery_person.html', {
                'form_data': form_data,
                'is_staff': staff_district is not None,
                'districts': districts,
                'staff_district': staff_district,
            })
        
        if not password or len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'dashboard/pages/delivery/create_delivery_person.html', {
                'form_data': form_data,
                'is_staff': staff_district is not None,
                'districts': districts,
                'staff_district': staff_district,
            })
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'dashboard/pages/delivery/create_delivery_person.html', {
                'form_data': form_data,
                'is_staff': staff_district is not None,
                'districts': districts,
                'staff_district': staff_district,
            })
        
        if not phone or not address:
            messages.error(request, 'Phone and address are required.')
            return render(request, 'dashboard/pages/delivery/create_delivery_person.html', {
                'form_data': form_data,
                'is_staff': staff_district is not None,
                'districts': districts,
                'staff_district': staff_district,
            })
        
        if not district:
            messages.error(request, 'District is required.')
            return render(request, 'dashboard/pages/delivery/create_delivery_person.html', {
                'form_data': form_data,
                'is_staff': staff_district is not None,
                'districts': districts,
                'staff_district': staff_district,
            })
        
        try:
            # Auto-generate username from email
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            
            # Create UserRole
            role, created = UserRole.objects.get_or_create(user=user)
            role.role = 'delivery'
            role.save()
            
            # Create DeliveryPerson profile with district
            DeliveryPerson.objects.create(
                user=user,
                phone=phone,
                address=address,
                district=district,
                is_active=True
            )
            
            messages.success(request, f'Delivery person {first_name} {last_name} created successfully.')
            return redirect('admin_delivery_persons_list')
            
        except IntegrityError:
            messages.error(request, 'An error occurred while creating the account.')
            return render(request, 'dashboard/pages/delivery/create_delivery_person.html', {
                'form_data': form_data,
                'is_staff': staff_district is not None,
                'districts': districts,
                'staff_district': staff_district,
            })
    
    # GET request - show form with districts
    return render(request, 'dashboard/pages/delivery/create_delivery_person.html', {
        'form_data': form_data,
        'is_staff': staff_district is not None,
        'districts': districts,
        'staff_district': staff_district,
    })


@staff_or_admin_required
def admin_delivery_person_edit(request, pk, **kwargs):
    """Edit delivery person (staff can only edit their own district)"""
    staff_district = getattr(request, 'staff_district', None)
    delivery_person = get_object_or_404(DeliveryPerson, id=pk)
    
    # Load all districts from nepal_provinces.json
    try:
        json_path = os.path.join(settings.BASE_DIR, 'static/data/nepal_provinces.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            nepal_data = json.load(f)
        
        # Extract all districts from all provinces
        districts = []
        for province in nepal_data:
            districts.extend(province.get('districts', []))
        districts = sorted(list(set(districts)))
    except:
        districts = []
    
    # Permission check: staff can only edit delivery persons in their district
    if staff_district and delivery_person.district != staff_district:
        messages.error(request, 'You do not have permission to edit this delivery person!')
        return redirect('admin_delivery_persons_list')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        district = request.POST.get('district', '').strip() if not staff_district else delivery_person.district
        
        # Validation
        if not first_name or not last_name:
            messages.error(request, 'First name and last name are required.')
            return render(request, 'dashboard/pages/delivery/edit_delivery_person.html', {
                'delivery_person': delivery_person,
                'is_staff': staff_district is not None,
                'districts': districts,
            })
        
        if not phone or not address:
            messages.error(request, 'Phone and address are required.')
            return render(request, 'dashboard/pages/delivery/edit_delivery_person.html', {
                'delivery_person': delivery_person,
                'is_staff': staff_district is not None,
                'districts': districts,
            })
        
        if not district:
            messages.error(request, 'District is required.')
            return render(request, 'dashboard/pages/delivery/edit_delivery_person.html', {
                'delivery_person': delivery_person,
                'is_staff': staff_district is not None,
                'districts': districts,
            })
        
        # Update user
        delivery_person.user.first_name = first_name
        delivery_person.user.last_name = last_name
        delivery_person.user.save()
        
        # Update delivery person
        delivery_person.phone = phone
        delivery_person.address = address
        delivery_person.is_active = is_active
        # Staff cannot change district
        if not staff_district:
            delivery_person.district = district
        delivery_person.save()
        
        messages.success(request, f'Delivery person {first_name} {last_name} updated successfully.')
        return redirect('admin_delivery_persons_list')
    
    context = {
        'delivery_person': delivery_person,
        'is_staff': staff_district is not None,
        'districts': districts,
    }
    return render(request, 'dashboard/pages/delivery/edit_delivery_person.html', context)

@staff_or_admin_required
def admin_delivery_person_delete(request, pk, **kwargs):
    """Delete delivery person (staff can only delete their own district)"""
    staff_district = getattr(request, 'staff_district', None)
    delivery_person = get_object_or_404(DeliveryPerson, id=pk)
    
    # Permission check: staff can only delete delivery persons in their district
    if staff_district and delivery_person.district != staff_district:
        messages.error(request, 'You can only delete delivery persons in your assigned district.')
        return redirect('admin_delivery_persons_list')
    
    # Store name for success message
    person_name = delivery_person.user.get_full_name()
    user = delivery_person.user
    
    # Delete the associated user (which cascades to delete DeliveryPerson)
    user.delete()
    
    messages.success(request, f'Delivery person "{person_name}" deleted successfully.')
    return redirect('admin_delivery_persons_list')
# ========================
#  Delivery Assignment Management (Admin)
# ========================

@staff_or_admin_required
def admin_delivery_assignments_list(request):
    """List delivery assignments (staff scoped to their district)"""
    staff_district = getattr(request, 'staff_district', None)
    status_filter = request.GET.get('status', '')
    
    if staff_district:
        assignments = DeliveryAssignment.objects.filter(
            delivery_person__district=staff_district
        ).select_related('order', 'delivery_person').order_by('-assigned_at')
    else:
        assignments = DeliveryAssignment.objects.all().select_related('order', 'delivery_person').order_by('-assigned_at')
    
    if status_filter:
        assignments = assignments.filter(status=status_filter)
    
    context = {
        'assignments': assignments,
        'status_choices': DeliveryAssignment.STATUS_CHOICES,
        'selected_status': status_filter,
    }
    
    return render(request, 'dashboard/pages/delivery/assignments_list.html', context)


@staff_or_admin_required
def admin_assign_order(request):
    """Assign multiple orders to a delivery person (staff scoped by district)"""
    staff_district = getattr(request, 'staff_district', None)

    if request.method == 'POST':
        delivery_person_id = request.POST.get('delivery_person')
        order_ids = request.POST.getlist('orders[]')

        if not order_ids:
            messages.error(request, 'Please select at least one order.')
            return redirect('admin_assign_order')

        if not delivery_person_id:
            messages.error(request, 'Please select a delivery person.')
            return redirect('admin_assign_order')

        try:
            delivery_person = DeliveryPerson.objects.get(id=delivery_person_id)
            # Staff permission check: ensure delivery person is in their district
            if staff_district and delivery_person.district != staff_district:
                messages.error(request, 'You can only assign orders to delivery persons in your district.')
                return redirect('admin_assign_order')

            created_count = 0
            failed_count = 0

            for order_id in order_ids:
                try:
                    order = Order.objects.get(id=order_id)
                    # Check if order is already assigned
                    if DeliveryAssignment.objects.filter(order=order).exists():
                        failed_count += 1
                        continue
                    DeliveryAssignment.objects.create(
                        order=order,
                        delivery_person=delivery_person,
                        status='assigned'
                    )
                    order.status = 'assigned'
                    order.save()
                    created_count += 1
                except Order.DoesNotExist:
                    failed_count += 1
                    continue

            if created_count > 0:
                if failed_count > 0:
                    messages.success(request, f'{created_count} order(s) assigned. {failed_count} order(s) skipped (already assigned or invalid).')
                else:
                    messages.success(request, f'{created_count} order(s) assigned to {delivery_person.user.get_full_name()}')
            else:
                messages.error(request, 'No orders could be assigned. (All may already be assigned)')

            return redirect('admin_delivery_assignments_list')

        except DeliveryPerson.DoesNotExist:
            messages.error(request, 'Delivery person not found.')
        except Exception as e:
            messages.error(request, f'Error assigning orders: {str(e)}')

        return redirect('admin_assign_order')

    # GET request - show form
    assigned_order_ids = DeliveryAssignment.objects.values_list('order_id', flat=True)
    unassigned_orders = Order.objects.exclude(id__in=assigned_order_ids).filter(
        status__in=['received', 'preparing', 'ready']
    ).order_by('-created_at')

    # Staff scoping: filter orders by restaurant district
    if staff_district:
        unassigned_orders = unassigned_orders.filter(
            items__menu_item__restaurant__city__iexact=staff_district
        ).distinct()

    # Delivery persons: filter by district for staff
    if staff_district:
        delivery_persons = DeliveryPerson.objects.filter(
            is_active=True,
            district=staff_district
        ).order_by('user__first_name')
    else:
        delivery_persons = DeliveryPerson.objects.filter(
            is_active=True
        ).order_by('user__first_name')

    context = {
        'unassigned_orders': unassigned_orders,
        'delivery_persons': delivery_persons,
    }
    return render(request, 'dashboard/pages/delivery/assign_order.html', context)

@staff_or_admin_required
def admin_assignment_details(request, assignment_id):
    """Return assignment details as JSON for modal (staff scoped by district)"""
    assignment = get_object_or_404(DeliveryAssignment, id=assignment_id)
    
    # Permission check: staff can only view assignments for their district's delivery persons
    staff_district = getattr(request, 'staff_district', None)
    if staff_district and assignment.delivery_person.district != staff_district:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to view this assignment.'
        }, status=403)
    
    return JsonResponse({
        'order_number': assignment.order.order_number,
        'customer_name': assignment.order.full_name,
        'customer_phone': assignment.order.phone,
        'address': f"{assignment.order.address}, {assignment.order.city}, {assignment.order.province}",
        'total': str(assignment.order.total),
        'delivery_person_name': assignment.delivery_person.user.get_full_name(),
        'delivery_person_phone': assignment.delivery_person.phone,
        'status_display': assignment.get_status_display(),
        'assigned_at': assignment.assigned_at.strftime('%Y-%m-%d %H:%M') if assignment.assigned_at else None,
        'picked_up_at': assignment.picked_up_at.strftime('%Y-%m-%d %H:%M') if assignment.picked_up_at else None,
        'in_transit_at': assignment.in_transit_at.strftime('%Y-%m-%d %H:%M') if assignment.in_transit_at else None,
        'delivered_at': assignment.delivered_at.strftime('%Y-%m-%d %H:%M') if assignment.delivered_at else None,
        'notes': assignment.notes,
        'failure_reason': assignment.failure_reason,
        'delivery_photo': assignment.delivery_photo.url if assignment.delivery_photo else None,
    })

# ===================
# Vendor Management
# ===================
# Vendor Management

@login_required
def restaurant_order_change_status(request, order_number):
    """Restaurant endpoint to change order status"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
    
    restaurant = get_object_or_404(Restaurant, user=request.user)
    order = get_object_or_404(Order, order_number=order_number)
    
    # Verify restaurant owns items in this order
    if not order.items.filter(menu_item__restaurant=restaurant).exists():
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    
    new_status = request.POST.get('status')
    
    if new_status not in dict(Order.STATUS_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    
    order.status = new_status
    if new_status == 'delivered':
        order.delivered_at = timezone.now()
    order.save()
    
    return JsonResponse({'success': True})

@staff_or_admin_required
def admin_restaurant_list(request):
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    selected_city = request.GET.get('city', '').strip()

    restaurants = Restaurant.objects.all().order_by('-created_at')
    if getattr(request, 'staff_district', None):
        restaurants = restaurants.filter(city__iexact=request.staff_district)

    if search:
        restaurants = restaurants.filter(
            Q(restaurant_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(phone__icontains=search) |
            Q(user__username__icontains=search)
        )

    if status_filter:
        restaurants = restaurants.filter(verification_status=status_filter)

    if selected_city:
        restaurants = restaurants.filter(city__iexact=selected_city)

    # Build city list for dropdown
    cities_qs = Restaurant.objects.all()
    if getattr(request, 'staff_district' , None):
        cities_qs = cities_qs.filter(city__iexact=request.staff_district)
    cities = list(
        cities_qs.exclude(city__isnull=True)
                 .exclude(city__exact='')
                 .values_list('city', flat=True)
                 .distinct()
                 .order_by('city')
    )



    return render(request, 'dashboard/pages/restaurant/restaurants_list.html', {
        'vendors': restaurants,
        'restaurant': Restaurant.objects.first(),
        'cities':cities,
        'selected_city': selected_city
        })

@staff_or_admin_required
def admin_restaurant_pending_kyc(request):
    restaurants = Restaurant.objects.filter(verification_status='pending').order_by('-created_at')
    return render(request, 'dashboard/pages/restaurant/pending_restaurants.html', {'vendors': restaurants})

@staff_or_admin_required
def admin_restaurant_verified_kyc(request):
    restaurants = Restaurant.objects.filter(verification_status='verified').order_by('-created_at')
    return render(request, 'dashboard/pages/restaurant/verified_restaurants.html', {'vendors': restaurants})



import random
import string
from django.core.mail import send_mail


@staff_or_admin_required
def admin_restaurant_add(request):
    # Load Nepal locations directly in the view
    locations_path = os.path.join(settings.BASE_DIR, 'static', 'nepal_provinces.json')
    try:
        with open(locations_path, 'r', encoding='utf-8') as f:
            nepal_locations = json.load(f)
    except FileNotFoundError:
        # Try alternative path
        locations_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'nepal_provinces.json')
        try:
            with open(locations_path, 'r', encoding='utf-8') as f:
                nepal_locations = json.load(f)
        except FileNotFoundError:
            nepal_locations = []
            messages.warning(request, 'Location data file not found')
    
    # Province name to choice key mapping
    province_mapping = {
        'Koshi Province': 'province1',
        'Madhesh Province': 'madhesh',
        'Bagmati Province': 'bagmati',
        'Gandaki Province': 'gandaki',
        'Lumbini Province': 'lumbini',
        'Karnali Province': 'karnali',
        'Sudurpashchim Province': 'sudurpashchim',
    }
    
    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email', '').strip().lower()
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return redirect('admin_restaurant_add')
            
            user = User.objects.create_user(
                username=email,
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            random_password = ''.join(random.choices(string.ascii_letters + string.digits + "@#$%&", k=10))
            user.set_password(random_password)
            user.save()
            
            # Create restaurant role
            UserRole.objects.create(user=user, role='restaurant')
            
            # enforce staff district (if user is staff, force restaurant.city to staff district)
            staff_district = getattr(request, 'staff_district', None)
            if staff_district:
                city = staff_district.strip()
                # Find province for staff district
                province_name = ''
                for prov in nepal_locations:
                    if city in prov.get('districts', []):
                        province_name = prov['province']
                        break
            else:
                city = request.POST.get('city', '').strip()
                province_name = request.POST.get('province', '')
            
            # Convert province name to choice key
            province_key = province_mapping.get(province_name, '')
            
            # Get latitude and longitude from POST data (optional)
            latitude = request.POST.get('latitude', '').strip()
            longitude = request.POST.get('longitude', '').strip()
            
            # Create restaurant
            restaurant = Restaurant.objects.create(
                user=user,
                restaurant_name=request.POST.get('shop_name'),
                phone=request.POST.get('phone'),
                address=request.POST.get('address'),
                city=city,
                province=province_key,  # Use the mapped key, not the display name
                pan_number=request.POST.get('pan_number'),
                citizenship_number=request.POST.get('citizenship_number', ''),
                verification_status='verified',
                is_active=True,
                latitude=Decimal(latitude) if latitude else None,
                longitude=Decimal(longitude) if longitude else None,
            )
            
            # Handle ALL file uploads
            if request.FILES.get('qr_image'):
                restaurant.qr_image = request.FILES['qr_image']
            
            if request.FILES.get('shop_logo'):
                restaurant.logo = request.FILES['shop_logo']
            
            if request.FILES.get('shop_banner'):
                restaurant.banner = request.FILES['shop_banner']
            
            if request.FILES.get('pan_document'):
                restaurant.pan_document = request.FILES['pan_document']
            
            if request.FILES.get('citizenship_front'):
                restaurant.citizenship_front = request.FILES['citizenship_front']
            
            if request.FILES.get('citizenship_back'):
                restaurant.citizenship_back = request.FILES['citizenship_back']
            
            if request.FILES.get('company_registration'):
                restaurant.company_registration = request.FILES['company_registration']
            
            restaurant.save()
            
            # Create wallet for restaurant
            RestaurantWallet.objects.get_or_create(restaurant=restaurant)
            
            # Send email with credentials
            try:
                send_mail(
                    subject='Your Restaurant Account Has Been Created',
                    message=f'''Hello {user.first_name},

Your restaurant account has been successfully created.

Login Credentials:
Email: {user.email}
Password: {random_password}

Please change your password after logging in.

Restaurant Details:
- Name: {restaurant.restaurant_name}
- Location: {restaurant.city}, {province_name}

Thank you for joining us!''',
                    from_email='info.nfc026@gmail.com',
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                messages.warning(request, f"Restaurant created, but email could not be sent: {e}")
            
            messages.success(request, f"Restaurant '{restaurant.restaurant_name}' created successfully!")
            return redirect('admin_restaurant_list')
            
        except Exception as e:
            messages.error(request, f"Error while creating restaurant: {str(e)}")
            return redirect('admin_restaurant_add')
    
    # GET request - load the form
    return render(request, 'dashboard/pages/restaurant/add_restaurant.html', {
        'nepal_locations': nepal_locations
    })


@staff_or_admin_required
def admin_restaurant_update(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    staff_district = getattr(request, 'staff_district', None)
    
    # Load Nepal locations directly in the view
    locations_path = os.path.join(settings.BASE_DIR, 'static', 'nepal_provinces.json')
    try:
        with open(locations_path, 'r', encoding='utf-8') as f:
            nepal_locations = json.load(f)
    except FileNotFoundError:
        # Try alternative path
        locations_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'nepal_provinces.json')
        try:
            with open(locations_path, 'r', encoding='utf-8') as f:
                nepal_locations = json.load(f)
        except FileNotFoundError:
            nepal_locations = []
            messages.warning(request, 'Location data file not found')
    
    # Province name to choice key mapping (reverse mapping)
    province_key_to_display = {
        'province1': 'Koshi Province',
        'madhesh': 'Madhesh Province',
        'bagmati': 'Bagmati Province',
        'gandaki': 'Gandaki Province',
        'lumbini': 'Lumbini Province',
        'karnali': 'Karnali Province',
        'sudurpashchim': 'Sudurpashchim Province',
    }
    
    # Staff district restriction check
    if staff_district:
        if (restaurant.city or '').strip().lower() != staff_district.strip().lower():
            messages.error(request, 'Forbidden: restaurant outside your district.')
            return redirect('admin_restaurant_list')

    if request.method == 'POST':
        try:
            # Update user info
            restaurant.user.first_name = request.POST.get('first_name')
            restaurant.user.last_name = request.POST.get('last_name')
            restaurant.user.email = request.POST.get('email', '').strip().lower()
            restaurant.user.save()
            
            # Update restaurant basic info
            restaurant.restaurant_name = request.POST.get('shop_name')
            restaurant.phone = request.POST.get('phone')
            restaurant.address = request.POST.get('address')
            
            # Handle district/staff restriction
            if staff_district:
                restaurant.city = staff_district
                # For staff, province should be determined by the district
                # Find province from nepal_locations
                for prov in nepal_locations:
                    if staff_district in prov.get('districts', []):
                        province_display_name = prov['province']
                        # Convert display name to choice key
                        for key, display in province_key_to_display.items():
                            if display == province_display_name:
                                restaurant.province = key
                                break
                        break
            else:
                # Admin can update province and district
                restaurant.city = request.POST.get('city', '').strip()
                province_display_name = request.POST.get('province', '').strip()
                # Convert display name to choice key
                for key, display in province_key_to_display.items():
                    if display == province_display_name:
                        restaurant.province = key
                        break
            
            # Get latitude and longitude from POST data (optional)
            latitude = request.POST.get('latitude', '').strip()
            longitude = request.POST.get('longitude', '').strip()
            
            # Update latitude and longitude if provided
            if latitude:
                restaurant.latitude = Decimal(latitude)
            if longitude:
                restaurant.longitude = Decimal(longitude)
            
            # Update KYC info
            restaurant.pan_number = request.POST.get('pan_number')
            restaurant.citizenship_number = request.POST.get('citizenship_number', '')
            restaurant.rejection_reason = request.POST.get('rejection_reason', '')
            
            # Update is_active (visible on platform) - works for both admin and staff
            is_visible = request.POST.get('is_visible')
            if is_visible is not None:  # Checkbox was present in form
                restaurant.is_active = True if is_visible else False
            
            # Only admin can change verification status
            if not staff_district:
                verification_status = request.POST.get('verification_status')
                if verification_status:
                    restaurant.verification_status = verification_status
            
            # Handle file uploads - Keep existing files if no new ones uploaded
            if request.FILES.get('qr_image'):
                # Delete old file if exists
                if restaurant.qr_image:
                    restaurant.qr_image.delete(save=False)
                restaurant.qr_image = request.FILES['qr_image']
            
            if request.FILES.get('shop_logo'):
                if restaurant.logo:
                    restaurant.logo.delete(save=False)
                restaurant.logo = request.FILES['shop_logo']
            
            if request.FILES.get('shop_banner'):
                if restaurant.banner:
                    restaurant.banner.delete(save=False)
                restaurant.banner = request.FILES['shop_banner']
            
            if request.FILES.get('pan_document'):
                if restaurant.pan_document:
                    restaurant.pan_document.delete(save=False)
                restaurant.pan_document = request.FILES['pan_document']
            
            if request.FILES.get('citizenship_front'):
                if restaurant.citizenship_front:
                    restaurant.citizenship_front.delete(save=False)
                restaurant.citizenship_front = request.FILES['citizenship_front']
            
            if request.FILES.get('citizenship_back'):
                if restaurant.citizenship_back:
                    restaurant.citizenship_back.delete(save=False)
                restaurant.citizenship_back = request.FILES['citizenship_back']
            
            if request.FILES.get('company_registration'):
                if restaurant.company_registration:
                    restaurant.company_registration.delete(save=False)
                restaurant.company_registration = request.FILES['company_registration']
            
            # Save all changes
            restaurant.save()
            
            messages.success(request, f'Restaurant "{restaurant.restaurant_name}" updated successfully!')
            return redirect('admin_restaurant_list')
            
        except Exception as e:
            messages.error(request, f'Error updating restaurant: {str(e)}')
            return redirect('admin_restaurant_update', pk=pk)
    
    # GET request - load the form
    # Get the display name for the current province key
    current_province_display = province_key_to_display.get(restaurant.province, '')
    
    return render(request, 'dashboard/pages/restaurant/edit_restaurant.html', {
        'restaurant': restaurant,
        'nepal_locations': nepal_locations,
        'current_province_display': current_province_display,  # Pass the display name to template
    })


@staff_or_admin_required
def admin_restaurant_delete(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    staff_district = getattr(request, 'staff_district', None)
    if staff_district:
        if (restaurant.city or '').strip().lower() != staff_district.strip().lower():
            messages.error(request, 'Forbidden: restaurant outside your district.')
            return redirect('admin_restaurant_list')
    
    # Check if restaurant has incomplete orders
    incomplete_orders = Order.objects.filter(
        items__menu_item__restaurant=restaurant
    ).exclude(status='delivered').distinct()
    
    if incomplete_orders.exists():
        messages.error(request, f"Cannot delete restaurant '{restaurant.restaurant_name}'. They have {incomplete_orders.count()} incomplete order(s).")
        return redirect('admin_restaurant_list')
    
    messages.success(request, f"Restaurant '{restaurant.restaurant_name}' deleted successfully")
    user = restaurant.user
    user.delete()
    return redirect('admin_restaurant_list')

@staff_or_admin_required
def admin_restaurant_change_status(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
    restaurant = get_object_or_404(Restaurant, pk=pk)
     # Staff scope check: only allow staff to change restaurants in their assigned district
    staff_district = getattr(request, 'staff_district', None)
    if staff_district:
        if (restaurant.city or '').strip().lower() != staff_district.strip().lower():
            return JsonResponse({'success': False, 'error': 'Forbidden: restaurant outside your district'}, status=403)

    new_status = request.POST.get('status')
    if new_status not in ['pending', 'verified', 'rejected']:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    restaurant.verification_status = new_status
    if new_status == 'verified':
        restaurant.verified_at = timezone.now()
        restaurant.is_active = True
    else:
        restaurant.is_active = False
    if new_status != 'rejected':
        restaurant.rejection_reason = ''
    restaurant.save()
    return JsonResponse({
        'success': True,
        'restaurant_id': restaurant.id,
        'verification_status': restaurant.verification_status,
        'verified_at': restaurant.verified_at.isoformat() if restaurant.verified_at else None,
        'is_active': restaurant.is_active,
    })


# For Making vendor Visible/Invisible on the platform

# from django.http import JsonResponse
# from django.views.decorators.http import require_POST

# For Making vendor Visible/Invisible on the platform (Independent of KYC)
# @admin_required
# @require_POST
# def admin_vendor_toggle_visibility(request, pk):
#     vendor = get_object_or_404(Vendor, pk=pk)

#     # Optional: still allow only verified vendors to be visible
#     # if vendor.verification_status != 'verified':
#     #     return JsonResponse({
#     #         'success': False,
#     #         'error': 'Only verified vendors can be made visible.'
#     #     })

#     vendor.is_visible = not getattr(vendor, 'is_visible', True)  # Default True if field missing
#     vendor.save()

#     return JsonResponse({
#         'success': True,
#         'is_visible': vendor.is_visible
#     })
# ===================
# Menu Item Management (Food Delivery)
# ===================
@staff_or_admin_required
def admin_menuItems_list(request):
    
    search = request.GET.get('search', '')
    cuisine_id = request.GET.get('category', '')
    restaurant_id = request.GET.get('vendor', '')
    menu_items = MenuItem.objects.all().order_by('-created_at')
        # Staff scoping: limit to restaurants in the staff's district
    staff_district = getattr(request, 'staff_district', None)
    if staff_district:
        menu_items = menu_items.filter(restaurant__city__iexact=staff_district)



    if search:
        menu_items = menu_items.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(restaurant__restaurant_name__icontains=search) |
            Q(section__name__icontains=search)
        )

    if cuisine_id:
        menu_items = menu_items.filter(section__id=cuisine_id)

    if restaurant_id:
        menu_items = menu_items.filter(restaurant_id=restaurant_id)

    sections = MenuSection.objects.filter(is_active=True)
    restaurants = Restaurant.objects.filter(is_active=True)
    if staff_district:
        restaurants = restaurants.filter(city__iexact=staff_district)


    return render(request, 'dashboard/pages/menuItem/menuItems_list.html', {
            'products': menu_items.distinct(),
            'categories': sections,
            'vendors': restaurants,
            
        })

@admin_required
def admin_menuItems_featured(request):
    search = request.GET.get('search', '')
    section_id = request.GET.get('category', '')
    restaurant_id = request.GET.get('vendor', '')
    menu_items = MenuItem.objects.filter(is_featured=True).order_by('-created_at')

    if search:
        menu_items = menu_items.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(restaurant__restaurant_name__icontains=search)
        )

    if section_id:
        menu_items = menu_items.filter(section_id=section_id)

    if restaurant_id:
        menu_items = menu_items.filter(restaurant_id=restaurant_id)

    sections = MenuSection.objects.filter(is_active=True)
    restaurants = Restaurant.objects.filter(is_active=True)

    return render(request, 'dashboard/pages/menuItem/featured_menuItems.html', {
        'products': menu_items,
        'categories': sections,
        'vendors': restaurants
    })

@admin_required
def admin_menuItems_low_stock(request):
    search = request.GET.get('search', '')
    section_id = request.GET.get('category', '')
    restaurant_id = request.GET.get('vendor', '')
    menu_items = MenuItem.objects.filter(quantity__gt=0, quantity__lte=F('low_quantity_alert')).order_by('quantity')

    if search:
        menu_items = menu_items.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(restaurant__restaurant_name__icontains=search)
        )

    if section_id:
        menu_items = menu_items.filter(section_id=section_id)

    if restaurant_id:
        menu_items = menu_items.filter(restaurant_id=restaurant_id)

    sections = MenuSection.objects.filter(is_active=True)
    restaurants = Restaurant.objects.filter(is_active=True)

    return render(request, 'dashboard/pages/product/low_stock_products.html', {
        'products': menu_items,
        'categories': sections,
        'vendors': restaurants
    })
    
    
def get_subcategories(request,category_id):
    subcategories=SubCategory.objects.filter(category__id=category_id).values_list('id','name')
    data=[{'id':id,'name':name} for id,name in subcategories]
    return JsonResponse(data,safe=False)


@staff_or_admin_required
def admin_menuItem_add(request):
    """Add a new menu item as admin/staff"""
    
    # Get the first active restaurant (since only one exists)
    restaurant = Restaurant.objects.filter(is_active=True, verification_status='verified').first()
    
    if not restaurant:
        messages.error(request, 'No active restaurant found. Please add a restaurant first.')
        return redirect('admin_restaurant_add')
    
    if request.method == 'POST':
        try:
            # Get form data (restaurant is auto-set, no need from POST)
            section_id = request.POST.get('menu_section')
            
            # Validate required fields
            if not section_id:
                messages.error(request, 'Menu Section is required.')
                return redirect('admin_menuItem_add')
            
            # Get menu section (ensure it belongs to the restaurant)
            menu_section = get_object_or_404(MenuSection, pk=section_id, restaurant=restaurant)
            
            # Create menu item
            menu_item = MenuItem.objects.create(
                restaurant=restaurant,
                section=menu_section,
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                price=Decimal(request.POST.get('price', '0')),
                prep_time=int(request.POST.get('prep_time', 15)),
                is_favorite=request.POST.get('is_favorite') == 'on',
                is_available=request.POST.get('is_available') == 'on',
                is_featured=request.POST.get('is_featured') == 'on',
                is_vegetarian=request.POST.get('is_vegetarian') == 'on',
            )
            
            # Handle main image
            if request.FILES.get('main_image'):
                menu_item.image = request.FILES['main_image']
                menu_item.save()
            
            # Handle dietary tags (many-to-many)
            dietary_tags = request.POST.getlist('dietary_tags')
            if dietary_tags:
                menu_item.dietary_tags.set(dietary_tags)
            
            messages.success(request, f'Menu item "{menu_item.name}" created successfully!')
            return redirect('admin_menuItems_list')
            
        except Exception as e:
            messages.error(request, f'Error creating menu item: {str(e)}')
            return redirect('admin_menuItem_add')
    
    # GET request - show form
    menu_sections = MenuSection.objects.filter(restaurant=restaurant, is_active=True).order_by('order', 'name')
    dietary_tags = FoodTag.objects.all().order_by('name')
    
    return render(request, 'dashboard/pages/menuItem/add_menuItem.html', {
        'restaurant': restaurant,
        'menu_sections': menu_sections,
        'dietary_tags': dietary_tags,
    })


@staff_or_admin_required
def admin_menuItem_update(request, pk):
    """Update an existing menu item"""
    menu_item = get_object_or_404(MenuItem, pk=pk)
    
    # Get the restaurant from the menu item
    restaurant = menu_item.restaurant
    
    if request.method == 'POST':
        try:
            # Get form data
            section_id = request.POST.get('menu_section')
            
            # Validate required fields
            if not section_id:
                messages.error(request, 'Menu Section is required.')
                return redirect('admin_menuItem_update', pk=pk)
            
            # Update menu item fields
            menu_item.section = get_object_or_404(MenuSection, pk=section_id, restaurant=restaurant)
            menu_item.name = request.POST.get('name')
            menu_item.description = request.POST.get('description', '')
            menu_item.price = Decimal(request.POST.get('price', '0'))
            menu_item.prep_time = int(request.POST.get('prep_time', 15))
            menu_item.is_favorite = request.POST.get('is_favorite') == 'on'
            menu_item.is_available = request.POST.get('is_available') == 'on'
            menu_item.is_featured = request.POST.get('is_featured') == 'on'
            menu_item.is_vegetarian = request.POST.get('is_vegetarian') == 'on'
            
            # Handle main image update
            if request.FILES.get('main_image'):
                # Delete old image if exists
                if menu_item.image:
                    menu_item.image.delete()
                menu_item.image = request.FILES['main_image']
            
            menu_item.save()
            
            # Update dietary tags
            dietary_tags = request.POST.getlist('dietary_tags')
            if dietary_tags:
                menu_item.dietary_tags.set(dietary_tags)
            else:
                menu_item.dietary_tags.clear()
            
            messages.success(request, f'Menu item "{menu_item.name}" updated successfully!')
            return redirect('admin_menuItems_list')
            
        except Exception as e:
            messages.error(request, f'Error updating menu item: {str(e)}')
            return redirect('admin_menuItem_update', pk=pk)
    
    # GET request - show form
    menu_sections = MenuSection.objects.filter(restaurant=restaurant, is_active=True).order_by('order', 'name')
    dietary_tags = FoodTag.objects.all().order_by('name')
    selected_tags = menu_item.dietary_tags.values_list('id', flat=True)
    
    return render(request, 'dashboard/pages/menuItem/edit_menuItem.html', {
        'menu_item': menu_item,
        'restaurant': restaurant,
        'menu_sections': menu_sections,
        'dietary_tags': dietary_tags,
        'selected_tags': selected_tags,
    })


@staff_or_admin_required
def admin_menuItem_delete(request, pk):
    """Delete a menu item"""
    menu_item = get_object_or_404(MenuItem, pk=pk)
    staff_district = getattr(request, 'staff_district', None)
    
    if staff_district:
        item_restaurant_city = getattr(menu_item.restaurant, 'city', '') or ''
        if item_restaurant_city.strip().lower() != staff_district.strip().lower():
            messages.error(request, 'Forbidden: item/restaurant outside your district.')
            return redirect('admin_menuItems_list')

    item_name = menu_item.name
    menu_item.delete()
    messages.success(request, f'Menu item "{item_name}" deleted successfully')
    return redirect('admin_menuItems_list')



# ==================
#  Menu Section Management
# ==================

@staff_or_admin_required
def admin_menu_sections_list(request):
    """List all menu sections with filters"""
    search = request.GET.get('search', '')
    restaurant_id = request.GET.get('restaurant', '')
    
    menu_sections = MenuSection.objects.all().order_by('restaurant', 'order', 'name')
    
    # Staff scoping: limit to restaurants in the staff's district
    staff_district = getattr(request, 'staff_district', None)
    if staff_district:
        menu_sections = menu_sections.filter(restaurant__city__iexact=staff_district)
    
    # Filter by search
    if search:
        menu_sections = menu_sections.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(restaurant__restaurant_name__icontains=search)
        )
    
    # Filter by restaurant
    if restaurant_id:
        menu_sections = menu_sections.filter(restaurant_id=restaurant_id)
    
    restaurants = Restaurant.objects.filter(is_active=True, verification_status='approved').order_by('restaurant_name')
    if staff_district:
        restaurants = restaurants.filter(city__iexact=staff_district)
    
    return render(request, 'dashboard/pages/menuSection/menu_sections_list.html', {
        'menu_sections': menu_sections,
        'restaurants': restaurants,
    })


@staff_or_admin_required
def admin_menu_section_add(request):
    """Add a new menu section"""
    
    # Get the active restaurant
    restaurant = Restaurant.objects.filter(
        is_active=True, 
        verification_status='verified'
    ).first()
    
    if not restaurant:
        messages.error(request, 'No active restaurant found. Please add a restaurant first.')
        return redirect('admin_restaurant_add')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            
            if not name:
                messages.error(request, 'Section name is required.')
                return redirect('admin_menu_section_add')
            
            # Check for duplicate names
            if MenuSection.objects.filter(restaurant=restaurant, name__iexact=name).exists():
                messages.error(request, f'Section "{name}" already exists for this restaurant.')
                return redirect('admin_menu_section_add')
            
            # Handle image upload
            image = request.FILES.get('image')
            
            # Create menu section
            menu_section = MenuSection.objects.create(
                restaurant=restaurant,
                name=name,
                description=request.POST.get('description', ''),
                image=image,
                order=int(request.POST.get('order', 0)),
                is_active=request.POST.get('is_active') == 'on',
            )
            
            messages.success(request, f'Menu section "{menu_section.name}" created successfully!')
            return redirect('admin_menu_sections_list')
            
        except Exception as e:
            messages.error(request, f'Error creating menu section: {str(e)}')
            return redirect('admin_menu_section_add')
    
    # GET request
    return render(request, 'dashboard/pages/menuSection/add_menu_section.html', {
        'restaurant': restaurant,
    })


@staff_or_admin_required
def admin_menu_section_edit(request, pk):
    """Edit an existing menu section"""
    menu_section = get_object_or_404(MenuSection, pk=pk)
    restaurant = menu_section.restaurant
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            
            if not name:
                messages.error(request, 'Section name is required.')
                return redirect('admin_menu_section_edit', pk=pk)
            
            # Check for duplicate names
            if MenuSection.objects.filter(restaurant=restaurant, name__iexact=name).exclude(pk=pk).exists():
                messages.error(request, f'Section "{name}" already exists for this restaurant.')
                return redirect('admin_menu_section_edit', pk=pk)
            
            # Handle image removal
            remove_image = request.POST.get('remove_image') == 'on'
            if remove_image and menu_section.image:
                menu_section.image.delete(save=False)
                menu_section.image = None
            
            # Handle new image upload
            image = request.FILES.get('image')
            if image:
                # Delete old image if it exists (and not already removed)
                if menu_section.image and not remove_image:
                    menu_section.image.delete(save=False)
                menu_section.image = image
            
            # Update other fields
            menu_section.name = name
            menu_section.description = request.POST.get('description', '')
            menu_section.order = int(request.POST.get('order', 0))
            menu_section.is_active = request.POST.get('is_active') == 'on'
            menu_section.save()
            
            messages.success(request, f'Menu section "{menu_section.name}" updated successfully!')
            return redirect('admin_menu_sections_list')
            
        except Exception as e:
            messages.error(request, f'Error updating menu section: {str(e)}')
            return redirect('admin_menu_section_edit', pk=pk)
    
    return render(request, 'dashboard/pages/menuSection/edit_menu_section.html', {
        'menu_section': menu_section,
        'restaurant': restaurant,
    })


@staff_or_admin_required
def admin_menu_section_delete(request, pk):
    """Delete a menu section"""
    menu_section = get_object_or_404(MenuSection, pk=pk)
    staff_district = getattr(request, 'staff_district', None)
    
    if staff_district:
        section_restaurant_city = getattr(menu_section.restaurant, 'city', '') or ''
        if section_restaurant_city.strip().lower() != staff_district.strip().lower():
            messages.error(request, 'Forbidden: section/restaurant outside your district.')
            return redirect('admin_menu_sections_list')
    
    section_name = menu_section.name
    try:
        menu_section.delete()
        messages.success(request, f'Menu section "{section_name}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting menu section: {str(e)}')
    
    return redirect('admin_menu_sections_list')

# ==================
#  Brand Management
# ==================

# @admin_required
# def admin_brand_list(request):
#     brands = Brand.objects.all().order_by('-created_at')
#     return render(request, 'dashboard/pages/brand/brand_list.html', {'brands': brands})


# @admin_required
# def admin_brand_add(request):
#     if request.method == 'POST':
#         name = request.POST.get('name')
        
#         # Validation
#         if not name:
#             messages.error(request, 'Brand name is required.')
#             return redirect('admin_brand_add')
        
#         # Check if brand already exists
#         if Brand.objects.filter(name__iexact=name).exists():
#             messages.error(request, 'A brand with this name already exists.')
#             return redirect('admin_brand_add')
        
#         # Create brand
#         try:
#             brand = Brand.objects.create(name=name)
#             messages.success(request, f'Brand "{brand.name}" created successfully!')
#             return redirect('admin_brand_list')
#         except Exception as e:
#             messages.error(request, f'Error creating brand: {str(e)}')
#             return redirect('admin_brand_add')
    
#     return render(request, 'dashboard/pages/brand/brand_add.html')


# @admin_required
# def admin_brand_update(request, brand_id):
#     brand = get_object_or_404(Brand, id=brand_id)
    
#     if request.method == 'POST':
#         name = request.POST.get('name')
        
#         # Validation
#         if not name:
#             messages.error(request, 'Brand name is required.')
#             return redirect('admin_brand_update', brand_id=brand_id)
        
#         # Check if another brand with this name exists
#         if Brand.objects.filter(name__iexact=name).exclude(id=brand_id).exists():
#             messages.error(request, 'A brand with this name already exists.')
#             return redirect('admin_brand_update', brand_id=brand_id)
        
#         # Update brand
#         try:
#             brand.name = name
#             brand.save()
#             messages.success(request, f'Brand "{brand.name}" updated successfully!')
#             return redirect('admin_brand_list')
#         except Exception as e:
#             messages.error(request, f'Error updating brand: {str(e)}')
#             return redirect('admin_brand_update', brand_id=brand_id)
    
#     return render(request, 'dashboard/pages/brand/brand_update.html', {'brand': brand})


# @admin_required
# def admin_brand_delete(request, brand_id):
#     brand = get_object_or_404(Brand, id=brand_id)
    
#     try:
#         brand_name = brand.name
#         brand.delete()
#         messages.success(request, f'Brand "{brand_name}" deleted successfully!')
#     except Exception as e:
#         messages.error(request, f'Error deleting brand: {str(e)}')
    
#     return redirect('admin_brand_list')


# ===================
# Category Management
# ===================

# @admin_required
# def admin_categories_list(request):
#     categories = CuisineType.objects.all().order_by('order', 'name')
#     return render(request, 'dashboard/pages/category/categories_list.html', {'categories': categories})

# @admin_required
# def admin_category_add(request):
#     if request.method == 'POST':

#         category = CuisineType.objects.create(
#             name=request.POST.get('name'),
        
#             order=int(request.POST.get('order', 0)),
#             is_featured=True if request.POST.get('is_featured') == 'on' else False
#         )
#         if request.FILES.get('image'):
#             category.image = request.FILES['image']
#         category.save()
#         return redirect('admin_categories_list')
#     return render(request, 'dashboard/pages/category/add_category.html')

# @admin_required
# def admin_category_update(request, pk):
#     category = get_object_or_404(Category, pk=pk)
#     if request.method == 'POST':
#         category.name = request.POST.get('name')
#         category.order = int(request.POST.get('order', 0))
#         category.is_featured = True if request.POST.get('is_featured') == 'on' else False
#         if request.FILES.get('image'):
#             category.image = request.FILES['image']
#         category.save()
#         return redirect('admin_categories_list')
#     return render(request, 'dashboard/pages/category/edit_category.html', {'category': category})

# @admin_required
# def admin_category_delete(request, pk):
#     category = get_object_or_404(Category, pk=pk)
#     category.delete()
#     return redirect('admin_categories_list')


# ===================
# Subcategory Management
# ===================
# Subcategory Management

# @admin_required
# def admin_subcategory_list(request):
#     subcategories = SubCategory.objects.all()
#     return render(request, 'dashboard/pages/subcategory/subcategory_list.html', {'subcategories': subcategories})

# @admin_required
# def admin_subcategory_add(request):
#     if request.method == "POST":
#         name = request.POST.get('name')
#         category_id = request.POST.get('category')
#         image = request.FILES.get('image')
        
#         category = Category.objects.get(id=category_id)
#         SubCategory.objects.create(
#         name=name,
#         category=category,
#         image=image
   
#         )
#         messages.success(request, "Subcategory added successfully.")
#         return redirect('admin_subcategory_list')
#     categories = Category.objects.all()
#     return render(request, 'dashboard/pages/subcategory/subcategory_add.html', {'categories': categories})


# @admin_required
# def admin_subcategory_update(request, subcategory_id):
#     subcategory = SubCategory.objects.get(id=subcategory_id)
#     categories = Category.objects.all()
#     if request.method == "POST":
#         subcategory.name = request.POST.get('name')
#         category_id = request.POST.get('category')
#         subcategory.category = Category.objects.get(id=category_id)
#         if request.FILES.get('image'):
#             subcategory.image = request.FILES['image']
#         subcategory.save()
#         messages.success(request, "Subcategory updated successfully.")
#         return redirect('admin_subcategory_list')
#     categories = Category.objects.all()
#     return render(request, 'dashboard/pages/subcategory/subcategory_edit.html', {
#         'subcategory': subcategory,
#         'categories': categories
#     })


# @admin_required
# def admin_subcategory_delete(request, subcategory_id):
#     subcategory = SubCategory.objects.get(id=subcategory_id)
#     subcategory.delete()
#     messages.success(request, "Subcategory deleted successfully.")
#     return redirect('admin_subcategory_list')

# from django.http import JsonResponse
# from .models import ChildCategory

# # dashboard/views.py
# @admin_required
# def admin_childcategory_list(request):
#     childcategories = ChildCategory.objects.select_related('subcategory').filter(is_active=True)
#     context = {
#         'childcategories': childcategories
#     }
#     return render(request, 'dashboard/pages/childcategory/childcategory_list.html', context)



# @login_required
# def get_childcategories(request, subcategory_id):
#     childcategories = ChildCategory.objects.filter(
#         subcategory_id=subcategory_id,
#         is_active=True
#     ).values('id', 'name')
#     return JsonResponse(list(childcategories), safe=False)


# @admin_required
# @admin_required
# def admin_childcategory_add(request):
#     categories = Category.objects.filter(is_active=True)  # list for dropdown
#     if request.method == 'POST':
#         name = request.POST.get('name')
#         category_id = request.POST.get('category')
#         subcategory_id = request.POST.get('subcategory')
#         image = request.FILES.get('image')

#         if not name or not category_id or not subcategory_id:
#             messages.error(request, "All fields are required!")
#             return redirect('admin_childcategory_add')

#         category = Category.objects.get(id=category_id)
#         subcategory = SubCategory.objects.get(id=subcategory_id)

#         # Create childcategory without image
#         ChildCategory.objects.create(
#             name=name,
#             image=request.FILES.get('image'),
#             subcategory=subcategory
#         )
#         messages.success(request, "Child category added successfully!")
#         return redirect('admin_childcategory_list')

#     context = {
#         'categories': categories,
#         'subcategories': []  # will populate via AJAX once category is selected
#     }
#     return render(request, 'dashboard/pages/childcategory/childcategory_add.html', context)


# @admin_required
# def admin_childcategory_update(request, childcategory_id):
#     childcategory = get_object_or_404(ChildCategory, id=childcategory_id)
#     categories = Category.objects.filter(is_active=True)
#     selected_category = childcategory.subcategory.category
#     subcategories = SubCategory.objects.filter(category=selected_category, is_active=True)

#     if request.method == 'POST':
#         name = request.POST.get('name')
#         subcategory_id = request.POST.get('subcategory')
#         # is_active = request.POST.get('is_active') == 'on'
#         image = request.FILES.get('image')

#         # Validate subcategory
#         try:
#             subcategory = SubCategory.objects.get(id=subcategory_id)
#         except SubCategory.DoesNotExist:
#             messages.error(request, "Selected subcategory does not exist.")
#             return redirect('admin_childcategory_update', childcategory_id=childcategory_id)

#         childcategory.name = name
#         childcategory.subcategory = subcategory
#         # childcategory.is_active = is_active
#         if image:
#             childcategory.image = image
#         childcategory.save()

#         messages.success(request, "Child category updated successfully!")
#         return redirect('admin_childcategory_list')

#     context = {
#         'childcategory': childcategory,
#         'categories': categories,
#         'subcategories': subcategories,
#         'selected_category': selected_category
#     }
#     return render(request, 'dashboard/pages/childcategory/childcategory_edit.html', context)





# @admin_required
# def admin_childcategory_delete(request, childcategory_id):
#     childcategory = get_object_or_404(ChildCategory, id=childcategory_id)
#     childcategory.delete()
#     messages.success(request, "Child category deleted successfully!")
#     return redirect('admin_childcategory_list')



# ===================
# Order Management
# ===================
# Order Management
@staff_or_admin_required
def admin_orders_list(request):
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    payment_status = request.GET.get('payment_status', '').strip()
    orders = Order.objects.all().order_by('-created_at')
    orders = _orders_for_staff(orders, request)

    selected_city = request.GET.get('city', '').strip()


    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(full_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    if status_filter:
        orders = orders.filter(status=status_filter)

    if payment_status:
        orders = orders.filter(payment_status=payment_status)

    if selected_city:
        orders = orders.filter(city__iexact=selected_city)

# Dropdown options sourced from actual orders (districts customers entered)
    cities_qs = (Order.objects
             .exclude(city__isnull=True)
             .exclude(city__exact='')
             .values_list('city', flat=True)
             .distinct()
             .order_by('city'))
    cities = list(cities_qs)


    return render(request, 'dashboard/pages/order/orders_list.html', {
        'orders': orders,
        'order_model': Order,
        'cities': cities,
        'selected_city': selected_city,
    })
    

@staff_or_admin_required
def admin_order_details(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    staff_district = getattr(request, 'staff_district', None)
    if staff_district:
        # show only items from vendors in staff district (partial view)
        order_items = order.items.filter(product__vendor__city__iexact=staff_district)
        partial = True
    else:
        order_items = order.items.all()
        partial = False


    return render(request, 'dashboard/pages/order/order_details.html', {
        'order': order,
        'order_items': order_items,
    })
    
    
    
# Payments Overview


@admin_required
def admin_payments_overview(request):
    search = request.GET.get('search', '')
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')

    # --- Restaurant Filter ---
    restaurants = Restaurant.objects.all().order_by('restaurant_name')
    if search:
        restaurants = restaurants.filter(restaurant_name__icontains=search)

    # --- Get All Delivered & Paid Orders ---
    orders = OrderItem.objects.select_related('order', 'menu_item__restaurant').filter(
        order__status='delivered',
        order__payment_status='paid'
    )

    # --- Date Filters (on Order created_at) ---
    if date_from:
        orders = orders.filter(order__created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(order__created_at__date__lte=date_to)

    # --- Commission Rate (Latest RestaurantCommission) ---
    commission_obj = RestaurantCommission.objects.order_by('-created_at').first()
    commission_rate = commission_obj.rate if commission_obj else Decimal('0.10')

    # --- Initialize Totals ---
    total_platform_revenue = Decimal('0.00')
    total_vendor_earnings = Decimal('0.00')
    total_payouts = Decimal('0.00')
    pending_total=Decimal('0.00')

    vendor_rows = []

    # --- Compute Per-Restaurant Aggregation ---
    for v in restaurants:
        # All delivered + paid order items for this restaurant
        restaurant_orders = orders.filter(menu_item__restaurant=v)

        gross_sales = Decimal('0.00')
        admin_commission_sum = Decimal('0.00')
        vendor_earning_sum = Decimal('0.00')
        


        for oi in restaurant_orders:
                    amount = Decimal(oi.get_total())
                    admin_commission = (amount * commission_rate).quantize(Decimal('0.01'))
                    vendor_earning = (amount - admin_commission).quantize(Decimal('0.01'))

                    gross_sales += amount
                    admin_commission_sum += admin_commission
                    vendor_earning_sum += vendor_earning

        # Get vendor wallet balance (total paid to vendor)
        wallet, _ = RestaurantWallet.objects.get_or_create(restaurant=v)
        vendor_wallet = wallet.balance.quantize(Decimal('0.01'))
        
        pending = RestaurantPayoutRequest.objects.filter(restaurant=v, status='pending').aggregate(total=Sum('requested_amount'))['total'] or Decimal('0.00')  
         
        # Update global totals
        pending_total += pending 
        total_platform_revenue += admin_commission_sum
        total_vendor_earnings += vendor_earning_sum
        total_payouts += RestaurantPayoutRequest.objects.filter(restaurant=v, status='paid').aggregate(total=Sum('requested_amount'))['total'] or Decimal('0.00')   

        vendor_rows.append({
            'vendor': v,
            'total_revenue': gross_sales,
            'admin_commission': admin_commission_sum,
            'vendor_earning': vendor_earning_sum,
            'wallet': vendor_wallet,
            'pending': pending,
        })

    # --- Prepare Context ---
    context = {
        'restaurant_rows': vendor_rows,
        'total_platform_revenue': total_platform_revenue.quantize(Decimal('0.01')),
        'total_vendor_earnings': total_vendor_earnings.quantize(Decimal('0.01')),
        'total_payouts': total_payouts.quantize(Decimal('0.01')),
        'pending_total':pending_total,
        'commission_rate_percent': (commission_rate * 100).quantize(Decimal('0.01')),
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(request, 'dashboard/pages/payment/overview.html', context)



@staff_or_admin_required
def admin_restaurant_payments_detail(request, vendor_id):
        restaurant = get_object_or_404(Restaurant, pk=vendor_id)
        
        commission_obj = RestaurantCommission.objects.order_by('-created_at').first()
        commission_rate = commission_obj.rate if commission_obj else Decimal('0.10')

        order_items = (
            OrderItem.objects.filter(menu_item__restaurant=restaurant, order__status='delivered', order__payment_status='paid')
            .select_related('order')
            .order_by('-order__created_at')
        )
        payouts = RestaurantPayoutRequest.objects.filter(restaurant=restaurant).order_by('-created_at')

        total_earning = Decimal('0')
        total_commission = Decimal('0')
        net_earning = Decimal('0')
        
        orders_data = []

        for oi in order_items:
            amount = Decimal(oi.get_total())
            admin_commission = (amount * commission_rate).quantize(Decimal('0.01'))
            vendor_earning = (amount - admin_commission).quantize(Decimal('0.01'))

            total_earning += amount
            net_earning += vendor_earning
            total_commission += admin_commission

            orders_data.append({
                'order': oi.order,
                'order_item': oi,
                'amount': amount,
                'admin_commission': admin_commission,
                'vendor_earning': vendor_earning,
                'payment_status': oi.order.payment_status,\
                    
            })
        wallet, _ = VendorWallet.objects.get_or_create(vendor=vendor)
        wallet = wallet.balance
        

        context = {
            'restaurant': restaurant,
            'orders_data': orders_data,
            'payouts': payouts,
            'total_earning': total_earning,
            'total_commission': total_commission,
            'wallet_balance': wallet,
            'net_earning': net_earning,
            'commission_rate_percent': (commission_rate * 100).quantize(Decimal('0.01')),
        }

        return render(request, 'dashboard/pages/payment/payment_detail.html', context)



# commission update api

@admin_required
def admin_update_commission(request):
    commission = RestaurantCommission.objects.first()
    if not commission:
        commission = RestaurantCommission.objects.create(rate=Decimal('0.10'))   
    new_rate = request.POST.get('rate')
    if not new_rate:
        return JsonResponse({'success': False, 'error': 'Rate is required'}, status=400)
    try:
        new_rate_decimal = Decimal(new_rate)
        if new_rate_decimal < 0 or new_rate_decimal > 1:
            return JsonResponse({'success': False, 'error': 'Rate must be between 0 and 1'}, status=400)
    except:
        return JsonResponse({'success': False, 'error': 'Invalid rate format'}, status=400)

    commission.rate = new_rate_decimal
    commission.updated_at = timezone.now()
    commission.save()

    return JsonResponse({
        'success': True,
        'rate': str(commission.rate),
        'updated_at': commission.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    })
    
# Payout Requests
@admin_required
def admin_payout_requests_list(request):
    status_filter = request.GET.get('status')
    requests_qs = RestaurantPayoutRequest.objects.select_related('restaurant').all().order_by('-created_at')
    if status_filter in ['pending','rejected', 'paid']:
        requests_qs = requests_qs.filter(status=status_filter)
    totals = {
        'pending': RestaurantPayoutRequest.objects.filter(status='pending').aggregate(total=Sum('requested_amount'))['total'] or 0,
        'rejected': RestaurantPayoutRequest.objects.filter(status='rejected').aggregate(total=Sum('requested_amount'))['total'] or 0,
        'paid': RestaurantPayoutRequest.objects.filter(status='paid').aggregate(total=Sum('requested_amount'))['total'] or 0,
    }
    return render(request, 'dashboard/pages/payout/requests_list.html', {'requests': requests_qs, 'totals': totals})

@admin_required
def admin_payout_requests_pending(request):
    status_filter = request.GET.get('status', '').strip() or 'pending'
    if status_filter not in ['pending', 'rejected', 'paid']:
        status_filter = 'pending'
    requests_qs = RestaurantPayoutRequest.objects.select_related('restaurant').filter(status=status_filter).order_by('-created_at')
    totals = {
        'pending': RestaurantPayoutRequest.objects.filter(status='pending').aggregate(total=Sum('requested_amount'))['total'] or 0,
        'rejected': RestaurantPayoutRequest.objects.filter(status='rejected').aggregate(total=Sum('requested_amount'))['total'] or 0,
        'paid': RestaurantPayoutRequest.objects.filter(status='paid').aggregate(total=Sum('requested_amount'))['total'] or 0,
    }
    return render(request, 'dashboard/pages/payout/pending_payouts.html', {'requests': requests_qs, 'totals': totals})

@admin_required
def admin_payout_requests_rejected(request):
    status_filter = request.GET.get('status', '').strip() or 'rejected'
    if status_filter not in ['pending','rejected', 'paid']:
        status_filter = 'rejected'
    requests_qs = RestaurantPayoutRequest.objects.select_related('restaurant').filter(status=status_filter).order_by('-created_at')
    totals = {
        'pending': RestaurantPayoutRequest.objects.filter(status='pending').aggregate(total=Sum('requested_amount'))['total'] or 0,
        'rejected': RestaurantPayoutRequest.objects.filter(status='rejected').aggregate(total=Sum('requested_amount'))['total'] or 0,
        'paid': RestaurantPayoutRequest.objects.filter(status='paid').aggregate(total=Sum('requested_amount'))['total'] or 0,
    }
    return render(request, 'dashboard/pages/payout/rejected_payouts.html', {'requests': requests_qs, 'totals': totals})

# Payout Request Status Change (JSON)
@admin_required
def admin_payout_request_change_status(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    req = get_object_or_404(RestaurantPayoutRequest, pk=pk)
    new_status = request.POST.get('status')

    if new_status not in ['pending', 'rejected', 'paid']:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

    req.status = new_status
    req.admin_response = request.POST.get('admin_response', '')
    req.save(update_fields=['status', 'admin_response'])
    messages.success(request, f'Payout request status updated to {new_status}.')
    return JsonResponse({
        'success': True,
        'status': new_status,
        'admin_response': req.admin_response
    })


@staff_or_admin_required
def admin_orders_pending(request):
    orders = Order.objects.filter(status__in=['pending', 'received', 'preparing', 'ready', 'assigned', 'picked_up', 'in_transit']).order_by('-created_at')
    orders = _orders_for_staff(orders, request)

    return render(request, 'dashboard/pages/order/pending_orders.html', {
        'orders': orders,
        'order_model': Order,
    })

@staff_or_admin_required
def admin_orders_delivered(request):
    orders = Order.objects.filter(status='delivered').order_by('-created_at')
    orders = _orders_for_staff(orders, request)
    return render(request, 'dashboard/pages/order/delivered_orders.html', {
        'orders': orders,
        'order_model': Order,
    })

@staff_or_admin_required
def admin_order_delete(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    order.delete()
    messages.success(request,f"Order ${order_number} deleted successfuly  ")
    return redirect('admin_orders_list')

@staff_or_admin_required
def admin_order_invoice_view(request,order_number):
    order=get_object_or_404(Order,order_number=order_number)
    invoices=Invoice.objects.filter(order=order)
    return render(request,'dashboard/pages/order/invoice_list.html',{'invoices':invoices,'order_number':order_number})
    

@staff_or_admin_required
def admin_invoice_detail(request, invoice_number):
    invoice = get_object_or_404(Invoice, invoice_number=invoice_number)
    
    # Ensure restaurant is loaded (sometimes select_related helps)
    invoice = Invoice.objects.select_related('restaurant', 'customer').get(invoice_number=invoice_number)
    
    return render(request, 'dashboard/pages/order/invoice_detail.html', {
        'invoice': invoice,
        'now': timezone.now(),
    })

    
    

@staff_or_admin_required
def admin_order_change_status(request, order_number):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
    order = get_object_or_404(Order, order_number=order_number)
    staff_district = getattr(request, 'staff_district', None)
    if staff_district:
               # allow staff only if order contains at least one item from their district
        if not order.items.filter(menu_item__restaurant__city__iexact=staff_district).exists():
            return JsonResponse({'success': False, 'error': 'Forbidden: not in your district'}, status=403)
    status = request.POST.get('status')
    payment_status = request.POST.get('payment_status')
    if status and status in dict(Order.STATUS_CHOICES):
        order.status = status
        if status == 'delivered':
            order.delivered_at = timezone.now()
    if payment_status and payment_status in dict(Order.PAYMENT_STATUS_CHOICES):
        order.payment_status = payment_status
    order.save()
    messages.success(request, 'Order updated successfully.')
    return JsonResponse({'success': True})


    

@staff_or_admin_required
def admin_order_items_json(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    staff_district = getattr(request, 'staff_district', None)
    if staff_district:
        if not order.items.filter(product__vendor__city__iexact=staff_district).exists():
                    return JsonResponse({'success': False, 'error': 'Forbidden: not in your district'}, status=403)


    items = []

    for item in order.items.select_related('product', 'variant').all():
        # Get all variants for the product
        all_variants = []
        for variant in item.product.variants.all():
            all_variants.append({
                'variant_type': variant.get_variant_type_display(),
                'name': variant.name,
                'price_adjustment': str(variant.price_adjustment),
            })

        items.append({
            'product_name': item.product.name,
            'selected_variant': item.variant.name if item.variant else '',
            'quantity': item.quantity,
            'price': str(item.price),
            'total': str(item.get_total()),
            'image_url': item.product.main_image.url if item.product.main_image else '',
            'all_variants': all_variants,
        })

    return JsonResponse({'success': True, 'items': items})



# Review Management
@admin_required
def admin_reviews_list(request):
    reviews = MenuItemReview.objects.all().order_by('-created_at')
    return render(request, 'dashboard/pages/review/reviews_list.html', {'reviews': reviews})

@admin_required
def admin_review_add(request):
    if request.method == 'POST':
        product_id = request.POST.get('product')
        user_id = request.POST.get('user')
        product = get_object_or_404(MenuItem, pk=product_id)
        user = get_object_or_404(User, pk=user_id)
        MenuItemReview.objects.create(
            menu_item=product,
            user=user,
            rating=int(request.POST.get('rating')),
            comment=request.POST.get('comment', '')
        )
        messages.success(request, 'Review added successfully.')
        return redirect('admin_reviews_list')
    products = MenuItem.objects.all()
    users = User.objects.all()
    return render(request, 'dashboard/pages/review/add_review.html', {'products': products, 'users': users})

@admin_required
def admin_review_update(request, pk):
    review = get_object_or_404(MenuItemReview, pk=pk)
    if request.method == 'POST':
        product_id = request.POST.get('product')
        user_id = request.POST.get('user')
        review.menu_item = get_object_or_404(MenuItem, pk=product_id)
        review.user = get_object_or_404(User, pk=user_id)
        review.rating = int(request.POST.get('rating'))
        review.comment = request.POST.get('comment', '')
        review.save()
        messages.success(request, 'Review updated successfully.')
        return redirect('admin_reviews_list')
    products = MenuItem.objects.all()
    users = User.objects.all()
    return render(request, 'dashboard/pages/review/edit_review.html', {'review': review, 'products': products, 'users': users})

@admin_required
def admin_review_delete(request, pk):
    review = get_object_or_404(MenuItemReview, pk=pk)
    review.delete()
    messages.success(request, 'Review deleted successfully.')
    return redirect('admin_reviews_list')



#============================
#   Contact Management
# ============================
@admin_required
def admin_contacts_list(request):
    search = request.GET.get('search', '')
    contacts = Contact.objects.all().order_by('-created_at')

    return render(request, 'dashboard/pages/contact/contact_list.html', {'contacts': contacts})

@admin_required
def admin_contacts_unread(request):
    contacts = Contact.objects.filter(is_read=False).order_by('-created_at')
    return render(request, 'dashboard/pages/contact/contact_unread.html', {'contacts': contacts})


@admin_required
def admin_read_contact(request):
    contact_id=request.GET.get('id')
    is_read=request.GET.get('is_read','true').lower() == 'true'
    contact = get_object_or_404(Contact, id=contact_id)
    contact.is_read = is_read
    contact.save(update_fields=['is_read'])
    status = "read" if is_read else "unread"
    messages.success(request, f"Message from {contact.name} marked as {status}.")
    return redirect('admin_contacts_list') 

@admin_required
def admin_contact_delete(request, pk):
    contact = get_object_or_404(Contact, id=id)
    contact.delete()
    return redirect('admin_contacts_list')



# Shipping Cost Management
@admin_required
def admin_tax_rate_view(request):
    tax_rate=TaxRate.objects.first()  # get the only record
    return render(request, 'dashboard/pages/tax/tax_rate.html', {
        'tax_rate': tax_rate
    })


@admin_required
def admin_tax_rate_edit(request, id):
    tax_obj = get_object_or_404(TaxRate, id=id)

    if request.method == "POST":
        tax = request.POST.get("tax")
        tax_obj.tax = tax
        tax_obj.save()
        messages.success(request, "Tax rate updated successfully.")
        return redirect('admin_tax_rate')  
    return render(request, "dashboard/pages/tax/tax_rate_edit.html", {
        "tax_obj": tax_obj  # Pass full object, not just number
    })



# Newsletter Management
@admin_required
def admin_newsletter_list(request):
    subscribers = Newsletter.objects.all().order_by('-subscribed_at')
    return render(request, 'dashboard/pages/newsletter/newsletter_list.html', {'subscribers': subscribers})

@admin_required
def admin_newsletter_add(request):
    if request.method == 'POST':
        Newsletter.objects.create(
            email= request.POST.get('email', '').strip().lower()
        )
        messages.success(request, 'Subscriber added successfully.')
        return redirect('admin_newsletter_list')
    return render(request, 'dashboard/pages/newsletter/add_newsletter.html')

@admin_required
def admin_newsletter_update(request, pk):
    subscriber = get_object_or_404(Newsletter, pk=pk)
    if request.method == 'POST':
        subscriber.email =  request.POST.get('email', '').strip().lower()
        subscriber.save()
        messages.success(request, 'Subscriber updated successfully.')
        return redirect('admin_newsletter_list')
    return render(request, 'dashboard/pages/newsletter/edit_newsletter.html', {'subscriber': subscriber})

@admin_required
def admin_newsletter_delete(request, pk):
    subscriber = get_object_or_404(Newsletter, pk=pk)
    subscriber.delete()
    messages.success(request, 'Subscriber deleted successfully.')
    return redirect('admin_newsletter_list')

# Slider Management
# Slider Management
@admin_required
def admin_sliders_list(request):
    sliders = Slider.objects.all().order_by('-created_at')
    return render(request, 'dashboard/pages/content/sliders_list.html', {'sliders': sliders})


@admin_required
def admin_slider_add(request):
    if request.method == 'POST':
        slider = Slider.objects.create(
            link=request.POST.get('link', ''),  # Only link is used
            is_active=request.POST.get('is_active') == 'on',  # Optional checkbox
        )

        if request.FILES.get('image'):
            slider.image = request.FILES['image']

        slider.save()
        messages.success(request, 'Slider created successfully.')
        return redirect('admin_sliders_list')

    return render(request, 'dashboard/pages/content/slider_add.html')


@admin_required
def admin_slider_update(request, pk):
    slider = get_object_or_404(Slider, pk=pk)

    if request.method == 'POST':
        slider.link = request.POST.get('link', '')
        slider.is_active = request.POST.get('is_active') == 'on'

        if request.FILES.get('image'):
            slider.image = request.FILES['image']

        slider.save()
        messages.success(request, 'Slider updated successfully.')
        return redirect('admin_sliders_list')

    return render(request, 'dashboard/pages/content/slider_update.html', {'slider': slider})


@admin_required
def admin_slider_delete(request, pk):
    slider = get_object_or_404(Slider, pk=pk)
    slider.delete()
    messages.success(request, 'Slider deleted successfully')
    return redirect('admin_sliders_list')


# Banner Management
@admin_required
def admin_banners_list(request):
    banners = Banner.objects.all().order_by('-created_at')
    return render(request, 'dashboard/pages/content/banners_list.html', {'banners': banners})

@admin_required
def admin_banner_add(request):
    used_pages = list(Banner.objects.values_list('page', flat=True))  # convert to list for JS

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        link = request.POST.get('link', '').strip()
        page = request.POST.get('page', '').strip()
        image = request.FILES.get('image')

        # Server-side check if page already exists
        if Banner.objects.filter(page=page).exists():
            messages.error(request, f"A banner for the page '{page}' already exists.")
            return render(
                request,
                'dashboard/pages/content/banner_add.html',
                {
                    'page_choices': Banner.PAGE_CHOICES,
                    'used_pages': used_pages,
                    'selected_page': page,
                    'title': title,
                    'link': link,
                }
            )

        try:
            banner = Banner.objects.create(
                title=title,
                link=link,
                page=page
            )
            if image:
                banner.image = image
                banner.save()

            messages.success(request, "Banner created successfully.")
            return redirect('admin_banners_list')

        except IntegrityError:
            messages.error(request, "A banner for this page already exists.")
            return redirect('admin_banner_add')

    return render(
        request,
        'dashboard/pages/content/banner_add.html',
        {
            'page_choices': Banner.PAGE_CHOICES,
            'used_pages': used_pages
        }
    )


@admin_required
def admin_banner_update(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    if request.method == 'POST':
        banner.title = request.POST.get('title', '')
        banner.link = request.POST.get('link', '')
        banner.page = request.POST.get('page','')
        banner.is_active = request.POST.get('is_active') == 'on'

        if request.FILES.get('image'):
            banner.image = request.FILES['image']

        banner.save()
        messages.success(request, 'Banner updated successfully.')
        return redirect('admin_banners_list')
    
    return render(request, 'dashboard/pages/content/banner_update.html', {'banner': banner,'page_choices':Banner.PAGE_CHOICES})



@admin_required
def admin_banner_delete(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    banner.delete()
    messages.success(request,'Banner deleted successfully')
    return redirect('admin_banners_list')


# Coupon Management
@admin_required
def admin_coupons_list(request):
    coupons = Coupon.objects.all().order_by('-created_at')
    return render(request, 'dashboard/pages/coupon/coupons_list.html', {'coupons': coupons})

@admin_required
def admin_coupon_add(request):
    if request.method == 'POST':
        coupon = Coupon.objects.create(
            code=request.POST.get('code'),
            discount_type=request.POST.get('discount_type'),
            discount_value=Decimal(request.POST.get('discount_value')),
            min_purchase=Decimal(request.POST.get('min_purchase')),
            usage_limit=int(request.POST.get('usage_limit')) if request.POST.get('usage_limit') else None,
            usage_limit_per_user=int(request.POST.get('usage_limit_per_user')) if request.POST.get('usage_limit_per_user') else None,
            valid_from=request.POST.get('valid_from'),
            valid_to=request.POST.get('valid_to')
        )
        return redirect('admin_coupons_list')
    return render(request, 'dashboard/pages/coupon/add_coupon.html')

@admin_required
def admin_coupon_update(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        coupon.code = request.POST.get('code')
        coupon.discount_type = request.POST.get('discount_type')
        coupon.discount_value = Decimal(request.POST.get('discount_value'))
        coupon.min_purchase=Decimal(request.POST.get('min_purchase'))
        coupon.usage_limit = int(request.POST.get('usage_limit')) if request.POST.get('usage_limit') else None
        coupon.usage_limit_per_user = int(request.POST.get('usage_limit_per_user')) if request.POST.get('usage_limit_per_user') else None
        coupon.valid_from = request.POST.get('valid_from')
        coupon.valid_to = request.POST.get('valid_to')
        coupon.save()
        return redirect('admin_coupons_list')
    return render(request, 'dashboard/pages/coupon/edit_coupon.html', {'coupon': coupon})

@admin_required
def admin_coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.delete()
    messages.success(request,'Coupon deleted successfully')
    return redirect('admin_coupons_list')



# Organization Management
# View: Display Organization Info
@admin_required
def admin_organization_view(request):
    organization = Organization.objects.first()
    return render(request, 'dashboard/pages/organization/organization.html', {
        'organization': organization
    })

@admin_required
def admin_organization_update(request):
    organization = Organization.objects.first()
    if organization is None:
        organization = Organization.objects.create(
            name='',
            phone='',
            address='',
            email=''
        )
    if request.method == 'POST':
        print(request.POST)
        organization.name = request.POST.get('name')
        organization.phone = request.POST.get('phone')
        organization.email =  request.POST.get('email', '').strip().lower()
        
        organization.phone_secondary = request.POST.get('phone_secondary', '')
        organization.address = request.POST.get('address')
        organization.facebook = request.POST.get('facebook', '')
        organization.instagram = request.POST.get('instagram', '')
        organization.twitter = request.POST.get('twitter', '')
        organization.youtube = request.POST.get('youtube', '')
        organization.tiktok = request.POST.get('tiktok', '')
        if request.FILES.get('logo'):
            organization.logo = request.FILES['logo']
        organization.save()
        return redirect('admin_organization_view')
    return render(request, 'dashboard/pages/organization/edit_organization.html', {'organization': organization})

# Notification Management
@admin_required
def admin_notifications_list(request):
    search = request.GET.get('search', '')
    notifications = Notification.objects.all().order_by('-created_at')

    if search:
        notifications = notifications.filter(
            Q(title__icontains=search) |
            Q(message__icontains=search)
        )

    return render(request, 'admin/notifications_list.html', {'notifications': notifications})

@admin_required
def admin_notification_add(request):
    if request.method == 'POST':
        user_id = request.POST.get('user')
        user = get_object_or_404(User, pk=user_id)
        Notification.objects.create(
            user=user,
            notification_type=request.POST.get('notification_type'),
            title=request.POST.get('title'),
            message=request.POST.get('message'),
            link=request.POST.get('link', '')
        )
        return redirect('admin_notifications_list')
    users = User.objects.all()
    return render(request, 'admin/notification_add.html', {'users': users})

@admin_required
def admin_notification_update(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    if request.method == 'POST':
        user_id = request.POST.get('user')
        notification.user = get_object_or_404(User, pk=user_id)
        notification.notification_type = request.POST.get('notification_type')
        notification.title = request.POST.get('title')
        notification.message = request.POST.get('message')
        notification.link = request.POST.get('link', '')
        notification.save()
        return redirect('admin_notifications_list')
    users = User.objects.all()
    return render(request, 'admin/notification_update.html', {'notification': notification, 'users': users})

@admin_required
def admin_notification_delete(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    notification.delete()
    return redirect('admin_notifications_list')



# Admin Profile
@admin_required
def admin_profile_view(request):
    return  render(request,'dashboard/pages/profile/admin_profile.html')

@admin_required
def admin_profile_edit(request):
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email', '').strip().lower()
        user=request.user
        user.first_name=first_name
        user.last_name=last_name
        user.email=email
        user.save()
        messages.success(request,'Profile Updated Successfully')
        return redirect('admin_profile')
    return render(request,'dashboard/pages/profile/admin_profile_edit.html')

# =====================================
#   Restaurant  Dashboard
# =================================

@login_required
def restaurant_dashboard(request):
    user = request.user
    try:
        restaurant_user = Restaurant.objects.get(user=request.user)
    except Restaurant.DoesNotExist:
        if getattr(request.user, "role", None) and request.user.role.role == "staff":
            return redirect('staff_dashboard')
      
        return HttpResponseForbidden()
  
    
    if not restaurant_user.is_active:
        return render(request,'restaurant/kyc_unverified.html',{"restaurant":restaurant_user})
        
    menu_items = MenuItem.objects.filter(restaurant=restaurant_user)
    orders = Order.objects.filter(items__menu_item__restaurant=restaurant_user).distinct()

    # Last 30 days
    last_30_days = timezone.now() - timedelta(days=30)
    recent_orders = orders.filter(created_at__gte=last_30_days)

    # Group revenue by day
    daily_revenue = (
        recent_orders.filter(status='delivered')
        .values('created_at__date')
        .annotate(total=Sum('total'))
        .order_by('created_at__date')
    )

    labels = [str(item['created_at__date']) for item in daily_revenue]
    data = [float(item['total']) for item in daily_revenue]

    context = {
        'total_menu_items': menu_items.count(),
        'active_menu_items': menu_items.filter(is_available=True).count(),
        'unavailable_items': menu_items.filter(is_available=False).count(),
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'delivered_orders': orders.filter(status='delivered').count(),
        'total_revenue': orders.filter(status='delivered').aggregate(total=Sum('total'))['total'] or 0,
        'chart_labels': labels,
        'chart_data': data,
    }

    return render(request, 'restaurant/restaurant_dashboard.html', context)



# Menu Item Management (Restaurant Dashboard)
@login_required
def restaurant_menu_items_list(request):
    search = request.GET.get('search', '')
    section_id = request.GET.get('category', '')
    restaurant = Restaurant.objects.get(user=request.user)
    menu_items = MenuItem.objects.filter(restaurant=restaurant).order_by('-created_at')
    
    if search:
        menu_items = menu_items.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(section__name__icontains=search)
        )

    if section_id:
        menu_items = menu_items.filter(section_id=section_id)

    sections = MenuSection.objects.filter(is_active=True)


    return render(request, 'restaurant/menuItem/menu_items_list.html', {
        'menu_items': menu_items,
        'sections': sections,
    })





@login_required
def restaurant_menu_item_add(request):
    if request.method == 'POST':
        try:
            # Get restaurant
            restaurant = Restaurant.objects.get(user=request.user)
            
            # Get form data
            section_id = request.POST.get('section')
            
            # Validate required fields
            if not section_id:
                messages.error(request, 'Menu Section is required.')
                return redirect('restaurant_menu_item_add')
            
            # Get section
            section = get_object_or_404(MenuSection, pk=section_id, restaurant=restaurant)
            
            # Create menu item
            menu_item = MenuItem.objects.create(
                restaurant=restaurant,
                section=section,
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                price=Decimal(request.POST.get('price', '0')),
                cost_price=Decimal(request.POST.get('cost_price')) if request.POST.get('cost_price') else None,
                is_vegetarian=request.POST.get('is_vegetarian') == 'on',
                is_spicy=request.POST.get('is_spicy') == 'on',
                spicy_level=int(request.POST.get('spicy_level', 0)),
                prep_time=int(request.POST.get('prep_time', 15)),
                dietary_tags=request.POST.get('dietary_tags', ''),
                is_featured=request.POST.get('is_featured') == 'on',
            )
         
            # Handle image
            if request.FILES.get('image'):
                menu_item.image = request.FILES['image']
                menu_item.save()

            messages.success(request, f"Menu item '{menu_item.name}' added successfully!")
            return redirect('restaurant_menu_items_list')

        except Restaurant.DoesNotExist:
            messages.error(request, "Restaurant profile not found. Please contact administrator.")
            return redirect('restaurant_menu_items_list')
        except Exception as e:
            messages.error(request, f"An error occurred while adding the menu item: {str(e)}")
            return redirect('restaurant_menu_item_add')

    # GET request - show form
    try:
        restaurant = Restaurant.objects.get(user=request.user)
        sections = MenuSection.objects.filter(restaurant=restaurant, is_active=True).order_by('order')
    except Restaurant.DoesNotExist:
        sections = []
    
    return render(request, 'restaurant/menuItem/add_menu_item.html', {
        'sections': sections,
    })




@login_required
def restaurant_menu_item_update(request, pk):
    menu_item = get_object_or_404(MenuItem, pk=pk)
    
    # Ensure restaurant owns this menu item
    if menu_item.restaurant.user != request.user:
        messages.error(request, "You don't have permission to edit this menu item.")
        return redirect('restaurant_menu_items_list')
    
    if request.method == 'POST':
        try:
            # Get form data
            section_id = request.POST.get('section')
            
            # Update menu item fields
            if section_id:
                section = get_object_or_404(MenuSection, pk=section_id, restaurant=menu_item.restaurant)
                menu_item.section = section
            
            menu_item.name = request.POST.get('name')
            menu_item.description = request.POST.get('description')
            menu_item.price = Decimal(request.POST.get('price', '0'))
            menu_item.cost_price = Decimal(request.POST.get('cost_price')) if request.POST.get('cost_price') else None
            menu_item.is_vegetarian = request.POST.get('is_vegetarian') == 'on'
            menu_item.is_spicy = request.POST.get('is_spicy') == 'on'
            menu_item.spicy_level = int(request.POST.get('spicy_level', 0))
            menu_item.prep_time = int(request.POST.get('prep_time', 15))
            menu_item.dietary_tags = request.POST.get('dietary_tags', '')
            menu_item.is_featured = request.POST.get('is_featured') == 'on'
            menu_item.is_available = request.POST.get('is_available') == 'on'
            
            # Handle image update
            if request.FILES.get('image'):
                menu_item.image = request.FILES['image']
            
            menu_item.save()
            
            messages.success(request, f"Menu item '{menu_item.name}' updated successfully!")
            return redirect('restaurant_menu_items_list')
        
        except Exception as e:
            messages.error(request, f"Error updating menu item: {str(e)}")
            return redirect('restaurant_menu_item_update', pk=pk)
    
    # GET request
    sections = MenuSection.objects.filter(restaurant=menu_item.restaurant, is_active=True).order_by('order')
    
    return render(request, 'restaurant/menu_items/edit_menu_item.html', {
        'menu_item': menu_item,
        'sections': sections,
    })


@login_required
def restaurant_menu_items_unavailable(request):
    search = request.GET.get('search', '')
    restaurant = Restaurant.objects.get(user=request.user)
    menu_items = MenuItem.objects.filter(restaurant=restaurant, is_available=False)

    if search:
        menu_items = menu_items.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    sections = MenuSection.objects.filter(restaurant=restaurant, is_active=True)
 
    return render(request, 'restaurant/menu_items/unavailable_items.html', {
        'menu_items': menu_items,
        'sections': sections,
    })



@login_required
def restaurant_menu_item_delete(request, pk):
    
    menu_item = get_object_or_404(MenuItem, pk=pk)
    menu_item.delete()
    messages.success(request,"Menu item deleted successfully")
    return redirect('restaurant_menu_items_list')

@login_required
def restaurant_menu_sections_list(request):
    try:
        restaurant = Restaurant.objects.get(user=request.user)
        sections = MenuSection.objects.filter(restaurant=restaurant, is_active=True).order_by('order')
    except Restaurant.DoesNotExist:
        sections = []
    return render(request, 'restaurant/menuSection/menu_sections_list.html', {'sections': sections})

@login_required
def restaurant_menu_section_add(request):
    restaurant = Restaurant.objects.get(user=request.user)
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        order = int(request.POST.get('order', 0))
        MenuSection.objects.create(
            restaurant=restaurant,
            name=name,
            description=description,
            order=order,
            is_active=True
        )
        return redirect('restaurant_menu_sections_list')
    return render(request, 'restaurant/menuSection/add_menu_section.html')

# =====================
# Order Management
# ====================
@login_required
def restaurant_orders_list(request):
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    payment_status = request.GET.get('payment_status', '')
    restaurant = Restaurant.objects.get(user=request.user)
    orders = Order.objects.filter(
        items__menu_item__restaurant=restaurant).distinct().order_by('-created_at')  
    selected_city = request.GET.get('city', '').strip()
  

    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(user__first_name=search) |
            Q(user__email__icontains=search) |
            Q(user__profile__phone__icontains=search)
        )

    if status_filter:
        orders = orders.filter(status=status_filter)

    if payment_status:
        orders = orders.filter(payment_status=payment_status)

    if selected_city:
        orders = orders.filter(city__iexact=selected_city)

        # Build city/district options from this restaurant's orders
    cities_qs = (
        Order.objects
        .filter(items__menu_item__restaurant=restaurant)
        .exclude(city__isnull=True)
        .exclude(city__exact='')
        .values_list('city', flat=True)
        .distinct()
        .order_by('city')
    )
    cities = list(cities_qs)

    

    return render(request, 'restaurant/order/orders_list.html', {
        'orders': orders,
        'order_model': Order,
        'cities': cities,
        'selected_city': selected_city,
    })
    

@login_required
def restaurant_order_details(request, order_number):
    vendor = Vendor.objects.get(user=request.user)
    
    # Get the order first
    order = get_object_or_404(Order, order_number=order_number)
    
    # Verify that this vendor has at least one product in this order
    vendor_items = order.items.filter(product__vendor=vendor)
    if not vendor_items.exists():
        messages.error(request,"You don't have access to this order")
        return redirect('restaurant_orders_list')
        
    return render(request, 'restaurant/order/order_details.html', {
        'order': order,
        'vendor_items': vendor_items  # Optional: pass only vendor's items
    })
    
@login_required
def restaurant_orders_pending(request):
    restaurant=Restaurant.objects.get(user=request.user)
    orders = Order.objects.filter(
    items__menu_item__restaurant=restaurant, status='pending').distinct().order_by('-created_at')
    return render(request, 'restaurant/order/pending_orders.html', {
        'orders': orders,
        'order_model': Order,
    })

@login_required
def restaurant_orders_delivered(request):
    restaurant=Restaurant.objects.get(user=request.user)
    orders = Order.objects.filter(
    items__menu_item__restaurant=restaurant, status='delivered').distinct().order_by('-created_at')
    return render(request, 'restaurant/order/delivered_orders.html', {
        'orders': orders,
        'order_model': Order,
    })
    



@login_required
def restaurant_order_invoice_view(request,order_number):
    order=get_object_or_404(Order,order_number=order_number)
    invoices=Invoice.objects.filter(order=order)
    return render(request,'restaurant/order/invoice_list.html',{'invoices':invoices,'order_number':order_number})
    

@login_required
def restaurant_order_update_payment_status(request, order_number):
    
    if not Restaurant.objects.filter(user=request.user):
        messages.error(request,"Permission denied ")
        return JsonResponse({'success':False},status=403)
        
    order = get_object_or_404(Order, order_number=order_number)
    new_payment_status = request.POST.get('payment_status')
    transaction_id = request.POST.get('transaction_id', '').strip()

    order.payment_status = new_payment_status
    if transaction_id:
        order.transaction_id = transaction_id
    if new_payment_status == 'paid' and order.status == 'pending':
        order.status = 'delivered'
    order.save()
    messages.success(request, f'Payment status updated to "{new_payment_status}" for order {order_number}.')

    return JsonResponse({
        'success': True,
       
    })
    

@login_required
def restaurant_order_change_status_legacy(request, order_number):
    """Vendor endpoint to change order status"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
    
    vendor = get_object_or_404(Vendor, user=request.user)
    order = get_object_or_404(Order, order_number=order_number)
    
    # Verify vendor owns items in this order
    if not order.items.filter(product__vendor=vendor).exists():
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    
    new_status = request.POST.get('status')
    
    if new_status not in dict(Order.STATUS_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    
    order.status = new_status
    if new_status == 'delivered':
        order.delivered_at = timezone.now()
    order.save()
    
    return JsonResponse({'success': True})

# =============================
# Vendor Payouts
# =============================
@login_required
def restaurant_payouts_list(request):
    user = request.user
    vendor = Vendor.objects.get(user=user)

    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    payout_requests = VendorPayoutRequest.objects.filter(vendor=vendor)

    if search:
        payout_requests = payout_requests.filter(
            Q(admin_response__icontains=search)
        )

    if status_filter:
        payout_requests = payout_requests.filter(status=status_filter)

    totals = {
        'total_requested': payout_requests.aggregate(total=Sum('requested_amount'))['total'] or 0,
        'total_paid': payout_requests.filter(status='paid').aggregate(total=Sum('requested_amount'))['total'] or 0,
    }

    payout_requests = payout_requests.order_by('-created_at')

    return render(request, 'restaurant/payout/payout_request_list.html', {
        'payout_requests': payout_requests,
        'totals': totals,
        'status_filter': status_filter,
        'search': search
    })



@login_required
def restaurant_payout_requests_pending(request):
    """
    Display pending payout requests for the vendor.
    """
    vendor = Vendor.objects.get(user=request.user)
    payout_requests = VendorPayoutRequest.objects.filter(vendor=vendor, status='pending').order_by('-created_at')

    return render(request, 'restaurant/payout/pending_payout.html', {
        'payout_requests': payout_requests
    })


@login_required
def restaurant_payout_requests_rejected(request):
    """
    Display rejected payout requests for the vendor.
    """
    vendor = Vendor.objects.get(user=request.user)
    payout_requests = VendorPayoutRequest.objects.filter(vendor=vendor, status='rejected').order_by('-created_at')

    return render(request, 'restaurant/payout/rejected_payout.html', {
        'payout_requests': payout_requests
    })
    
    

@login_required
def restaurant_payout_request_add(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    wallet, _ = VendorWallet.objects.get_or_create(vendor=vendor)

    if request.method == 'POST':
        if VendorPayoutRequest.objects.filter(vendor=vendor, status="pending"):
            messages.error(
        request,
        "You already have a payout request that is pending. "
        "You can send a new request only after the previous one is paid or rejected."
    )
            return redirect('restaurant_payout_list')
        try:
            requested_amount = Decimal(request.POST.get('requested_amount', '0'))
        except:
            messages.error(request, "Invalid amount entered.")
            return redirect('restaurant_payout_requests_add')

        #  Validation checks
        if requested_amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect('restaurant_payout_requests_add')

        if requested_amount > wallet.balance:
            messages.error(request, "Insufficient balance for this payout request.")
            return redirect('restaurant_payout_requests_add')

        #  Create payout request (do NOT deduct balance yet)
        VendorPayoutRequest.objects.create(
            vendor=vendor,
            requested_amount=requested_amount,
            status='pending',  # initial status
            admin_response='',
        )

        messages.success(
            request, 
            " Payout request submitted successfully and is awaiting admin approval."
        )
        return redirect('restaurant_payout_list')

    context = {
        "vendor": vendor,
        "available_balance": wallet.balance,  # show wallet balance
    }
    return render(request, 'restaurant/payout/add_payout_request.html', context)


@login_required
def restaurant_wallet_view(request):
   
    vendor = get_object_or_404(Vendor, user=request.user)
    
    wallet, _ = VendorWallet.objects.get_or_create(vendor=vendor)
    orders = OrderItem.objects.filter(
        product__vendor=vendor,
        order__status='delivered',
        order__payment_status='paid'
    ).select_related('order').order_by('-order__created_at')
    
    context = {
        'vendor': vendor,
        'wallet': wallet,
        'orders': orders,
    }
    
    return render(request, 'restaurant/wallet/wallet.html', context)



# ========================
#  Vendor Product Review
# ========================
@login_required
def restaurant_menu_item_reviews_list(request):
    vendor=Vendor.objects.get(user=request.user)
    reviews = Review.objects.filter(product__vendor=vendor).order_by('-created_at')
    return render(request, 'restaurant/review/reviews_list.html', {'reviews': reviews})




# ===========================
# Invoice
# =========================
@login_required
def restaurant_invoices(request):
    vendor=Vendor.objects.get(user=request.user)
    invoices = Invoice.objects.filter(vendor=vendor).order_by('-created_at')
    return render(request, 'restaurant/invoice/invoices.html', {'invoices': invoices})



@login_required
def restaurant_invoice_detail(request, invoice_number):
    vendor = Vendor.objects.get(user=request.user) 
    invoice = get_object_or_404(Invoice, invoice_number=invoice_number, vendor=vendor) 
     
    order_items = invoice.order.items.filter(product__vendor=vendor)  # Only vendor's items
    total_shipping_cost = sum(
        (item.product.shipping_cost or Decimal('0')) * item.quantity 
        for item in order_items
    )
    total_shipping_cost = Decimal(str(total_shipping_cost))  # Ensure it's Decimal
    tax_obj = TaxRate.objects.first() 
    tax_rate = Decimal(str(tax_obj.tax)) if tax_obj else Decimal('0')
    tax_amount = (invoice.subtotal + total_shipping_cost) * (tax_rate / Decimal('100'))
 
    # Calculate total price
    discount = invoice.discount if invoice.discount else Decimal('0')
    total_price = invoice.subtotal + total_shipping_cost + tax_amount - discount
 
    return render(request, 'restaurant/invoice/invoice_detail.html', { 
        'invoice': invoice, 
        'order_items': order_items, 
        'shipping_cost': total_shipping_cost, 
        'tax_rate': tax_rate, 
        'tax_amount': tax_amount, 
        'total_price': total_price, 
    })

# ====================
# Vendor Profile
# ======================
@login_required
def restaurant_profile_view(request):
    vendor=Vendor.objects.get(user=request.user)
    return render(request,'restaurant/profile/restaurant_profile.html',{'restaurant':restaurant})


@login_required
def restaurant_profile_edit_view(request):
    vendor = Vendor.objects.get(user=request.user)
    
    if request.method == 'POST':
        vendor.shop_name = request.POST.get('shop_name', vendor.shop_name)
        vendor.description = request.POST.get('description', vendor.description)
        vendor.phone = request.POST.get('phone', vendor.phone)
        vendor.user.email = (request.POST.get('email') or vendor.user.email).strip().lower()
        vendor.address = request.POST.get('address', vendor.address)
        vendor.city = request.POST.get('city', vendor.city)
        vendor.province = request.POST.get('province', vendor.province)
        vendor.pan_number = request.POST.get('pan_number', vendor.pan_number)
        vendor.citizenship_number = request.POST.get('citizenship_number', vendor.citizenship_number)

        files = request.FILES
        if 'shop_logo' in files:
            vendor.shop_logo = files['shop_logo']
        if 'shop_banner' in files:
            vendor.shop_banner = files['shop_banner']
        
        vendor.save()
        return redirect('restaurant_profile')
    
    context = {'vendor': vendor}
    return render(request, 'restaurant/profile/restaurant_profile_edit.html', context)


from django.contrib.auth import update_session_auth_hash

@login_required
def change_password_view(request):

    user = request.user     
    # Staff cannot change their own password
    if hasattr(user, 'role') and user.role.role == 'staff':
        messages.error(request, 'Staff cannot change their own password. Contact admin to reset your password.')
        return redirect('staff_dashboard')
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

      

        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirmation do not match.")
        elif len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
        else:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user) 
            messages.success(request, "Password updated successfully.")
            if user.role.role=='admin':
                return redirect('admin_dashboard')
            elif user.role.role == 'vendor':
                return redirect('restaurant_profile')
            elif user.role.role == 'customer':
                return redirect('customer_profile')

    return render(request, 'dashboard/pages/change_password.html')



# ========================
#  Vendor Kyc Resubmit
# =======================
@login_required
def restaurant_resubmit_kyc(request):
    vendor=Vendor.objects.get(user=request.user)
    if request.method == "POST":
        try:
            pan_number = request.POST.get("pan_number")
            pan_document = request.FILES.get("pan_document")
            citizenship_front = request.FILES.get("citizenship_front")
            citizenship_back = request.FILES.get("citizenship_back")
            company_registration = request.FILES.get("company_registration")
            vendor.pan_number = pan_number
            vendor.pan_document = pan_document
            if citizenship_front:
                vendor.citizenship_front = citizenship_front

            if citizenship_back:
                vendor.citizenship_back = citizenship_back

            if company_registration:
                vendor.company_registration = company_registration

            # Reset verification status
            vendor.verification_status = "pending"
            vendor.rejection_reason = ""
            vendor.verified_at = None
            vendor.save()
        except Exception as e:
            messages.success(request,"Something went wrong")
            return render(request,'restaurant/resubmit_kyc.html')

        messages.success(request, "Your KYC documents were resubmitted successfully.")
        return redirect("vendor_dashboard")

    return render(request, "restaurant/resubmit_kyc.html", {"vendor": vendor})

# ===========================
# Ad Banner Management
# ==========================
from .models import AdBanner
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils import timezone
import pytz

@staff_or_admin_required
def admin_create_or_edit_ad_banner(request, banner_id=None):
    """
    View to create or edit ad banners without using Django forms
    """
    
    # If banner_id is provided, get the banner for editing
    if banner_id:
        banner = get_object_or_404(AdBanner, id=banner_id)
        is_edit = True
        title = "Edit Ad Banner"
        submit_btn_text = "Update Banner"
    else:
        banner = None
        is_edit = False
        title = "Create New Ad Banner"
        submit_btn_text = "Create Banner"
    
    # Get all restaurants for the dropdown
    restaurants = Restaurant.objects.filter(is_active=True).order_by('restaurant_name')
    
    # Handle form submission
    if request.method == 'POST':
        # Get data from POST request
        title_text = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        link_url = request.POST.get('link_url', '').strip()
        cta_text = request.POST.get('cta_text', 'Learn More').strip()
        restaurant_id = request.POST.get('restaurant')
        order = request.POST.get('order', 0)
        
        # FIXED: Handle checkbox value - check for 'on' (default) or '1'
        is_active = request.POST.get('is_active') in ['on', '1', True]
        
        # Handle date fields
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        # Process dates - keep them in local time (Nepal timezone)
        start_date = None
        end_date = None
        
        # Get Nepal timezone
        nepal_tz = pytz.timezone('Asia/Kathmandu')
        
        if start_date_str:
            try:
                # Parse the local datetime string
                naive_start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                # Make it aware in Nepal timezone
                start_date = nepal_tz.localize(naive_start_date)
                # Convert to UTC for storage
                start_date = start_date.astimezone(pytz.UTC)
            except ValueError:
                messages.error(request, 'Invalid start date format')
                return render(request, 'dashboard/pages/restaurant/create_or_edit_ad_banner.html', {
                    'banner': banner,
                    'restaurants': restaurants,
                    'is_edit': is_edit,
                    'title': title,
                    'submit_btn_text': submit_btn_text,
                })
        
        if end_date_str:
            try:
                # Parse the local datetime string
                naive_end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
                # Make it aware in Nepal timezone
                end_date = nepal_tz.localize(naive_end_date)
                # Convert to UTC for storage
                end_date = end_date.astimezone(pytz.UTC)
            except ValueError:
                messages.error(request, 'Invalid end date format')
                return render(request, 'dashboard/pages/restaurant/create_or_edit_ad_banner.html', {
                    'banner': banner,
                    'restaurants': restaurants,
                    'is_edit': is_edit,
                    'title': title,
                    'submit_btn_text': submit_btn_text,
                })
        
        # Handle image upload
        image = request.FILES.get('image')
        
        # Validation
        if not title_text:
            messages.error(request, 'Title is required')
            return render(request, 'dashboard/pages/restaurant/create_or_edit_ad_banner.html', {
                'banner': banner,
                'restaurants': restaurants,
                'is_edit': is_edit,
                'title': title,
                'submit_btn_text': submit_btn_text,
            })
        
        if not image and not is_edit:
            messages.error(request, 'Image is required for new banner')
            return render(request, 'dashboard/pages/restaurant/create_or_edit_ad_banner.html', {
                'banner': banner,
                'restaurants': restaurants,
                'is_edit': is_edit,
                'title': title,
                'submit_btn_text': submit_btn_text,
            })
        
        # Process restaurant
        restaurant = None
        if restaurant_id and restaurant_id != '':
            try:
                restaurant = Restaurant.objects.get(id=restaurant_id)
            except Restaurant.DoesNotExist:
                messages.error(request, 'Selected restaurant does not exist')
                return render(request, 'dashboard/pages/restaurant/create_or_edit_ad_banner.html', {
                    'banner': banner,
                    'restaurants': restaurants,
                    'is_edit': is_edit,
                    'title': title,
                    'submit_btn_text': submit_btn_text,
                })
        
        # Create or update banner
        if is_edit:
            # Update existing banner
            banner.title = title_text
            banner.description = description
            banner.link_url = link_url
            banner.cta_text = cta_text
            banner.restaurant = restaurant
            banner.order = int(order) if order else 0
            banner.is_active = is_active
            banner.start_date = start_date if start_date else timezone.now()
            banner.end_date = end_date
            
            if image:
                banner.image = image
            
            banner.save()
            messages.success(request, f'Ad banner "{banner.title}" has been updated successfully!')
            
        else:
            # Create new banner
            if not start_date:
                start_date = timezone.now()
            
            banner = AdBanner.objects.create(
                title=title_text,
                description=description,
                image=image,
                link_url=link_url,
                cta_text=cta_text,
                restaurant=restaurant,
                start_date=start_date,
                end_date=end_date,
                order=int(order) if order else 0,
                is_active=is_active
            )
            messages.success(request, f'Ad banner "{banner.title}" has been created successfully!')
        
        return redirect('admin_ad_banner_list')
    
    # For GET request, prepare initial data - convert UTC to local time for display
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    
    initial_start_date = ''
    initial_end_date = ''
    
    if banner and banner.start_date:
        # Convert UTC to local time for display
        local_start = banner.start_date.astimezone(nepal_tz)
        initial_start_date = local_start.strftime('%Y-%m-%dT%H:%M')
    
    if banner and banner.end_date:
        # Convert UTC to local time for display
        local_end = banner.end_date.astimezone(nepal_tz)
        initial_end_date = local_end.strftime('%Y-%m-%dT%H:%M')
    
    initial_data = {
        'title': banner.title if banner else '',
        'description': banner.description if banner else '',
        'link_url': banner.link_url if banner else '',
        'cta_text': banner.cta_text if banner else 'Learn More',
        'order': banner.order if banner else 0,
        'is_active': banner.is_active if banner else True,
        'restaurant_id': banner.restaurant.id if banner and banner.restaurant else '',
        'start_date': initial_start_date,
        'end_date': initial_end_date,
    }
    
    context = {
        'banner': banner,
        'restaurants': restaurants,
        'is_edit': is_edit,
        'title': title,
        'submit_btn_text': submit_btn_text,
        'initial': initial_data,
    }
    
    return render(request, 'dashboard/pages/restaurant/create_or_edit_ad_banner.html', context)


@staff_or_admin_required
def admin_ad_banner_list(request):
    """
    View to list all ad banners with filtering and pagination
    """
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    restaurant_filter = request.GET.get('restaurant', '')
    
    # Base queryset
    banners = AdBanner.objects.all().select_related('restaurant')
    
    # Apply filters
    if search_query:
        banners = banners.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'active':
            banners = banners.filter(is_active=True)
        elif status_filter == 'inactive':
            banners = banners.filter(is_active=False)
        elif status_filter == 'expired':
            banners = banners.filter(end_date__lt=timezone.now())
        elif status_filter == 'scheduled':
            banners = banners.filter(start_date__gt=timezone.now())
    
    if restaurant_filter:
        if restaurant_filter == 'global':
            banners = banners.filter(restaurant__isnull=True)
        else:
            banners = banners.filter(restaurant_id=restaurant_filter)
    
    # Order by order field, then by created_at
    banners = banners.order_by('order', '-created_at')
    
    # Pagination
    paginator = Paginator(banners, 10)  # Show 10 banners per page
    page = request.GET.get('page', 1)
    
    try:
        banners_page = paginator.page(page)
    except PageNotAnInteger:
        banners_page = paginator.page(1)
    except EmptyPage:
        banners_page = paginator.page(paginator.num_pages)
    
    # Get all restaurants for filter dropdown
    restaurants = Restaurant.objects.filter(is_active=True).order_by('restaurant_name')
    
    # Calculate statistics
    total_banners = AdBanner.objects.count()
    active_banners = AdBanner.objects.filter(is_active=True).count()
    expired_banners = AdBanner.objects.filter(end_date__lt=timezone.now(), is_active=True).count()
    scheduled_banners = AdBanner.objects.filter(start_date__gt=timezone.now(), is_active=True).count()
    
    context = {
        'banners': banners_page,
        'total_banners': total_banners,
        'active_banners': active_banners,
        'expired_banners': expired_banners,
        'scheduled_banners': scheduled_banners,
        'restaurants': restaurants,
        'search_query': search_query,
        'status_filter': status_filter,
        'restaurant_filter': restaurant_filter,
        'current_time': timezone.now(),
    }
    
    return render(request, 'dashboard/pages/restaurant/ad_banners.html', context)


@staff_or_admin_required
def admin_ad_banner_list(request):
    """
    View to list all ad banners with filtering and pagination
    """
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    restaurant_filter = request.GET.get('restaurant', '')
    
    # Base queryset
    banners = AdBanner.objects.all().select_related('restaurant')
    
    # Apply filters
    if search_query:
        banners = banners.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'active':
            banners = banners.filter(is_active=True)
        elif status_filter == 'inactive':
            banners = banners.filter(is_active=False)
        elif status_filter == 'expired':
            banners = banners.filter(end_date__lt=timezone.now())
        elif status_filter == 'scheduled':
            banners = banners.filter(start_date__gt=timezone.now())
    
    if restaurant_filter:
        if restaurant_filter == 'global':
            banners = banners.filter(restaurant__isnull=True)
        else:
            banners = banners.filter(restaurant_id=restaurant_filter)
    
    # Order by order field, then by created_at
    banners = banners.order_by('order', '-created_at')
    
    # Pagination
    paginator = Paginator(banners, 10)  # Show 10 banners per page
    page = request.GET.get('page', 1)
    
    try:
        banners_page = paginator.page(page)
    except PageNotAnInteger:
        banners_page = paginator.page(1)
    except EmptyPage:
        banners_page = paginator.page(paginator.num_pages)
    
    # Get all restaurants for filter dropdown
    restaurants = Restaurant.objects.filter(is_active=True).order_by('restaurant_name')
    
    # Calculate statistics
    total_banners = AdBanner.objects.count()
    active_banners = AdBanner.objects.filter(is_active=True).count()
    expired_banners = AdBanner.objects.filter(end_date__lt=timezone.now(), is_active=True).count()
    scheduled_banners = AdBanner.objects.filter(start_date__gt=timezone.now(), is_active=True).count()
    
    context = {
        'banners': banners_page,
        'total_banners': total_banners,
        'active_banners': active_banners,
        'expired_banners': expired_banners,
        'scheduled_banners': scheduled_banners,
        'restaurants': restaurants,
        'search_query': search_query,
        'status_filter': status_filter,
        'restaurant_filter': restaurant_filter,
        'current_time': timezone.now(),
    }
    
    return render(request, 'dashboard/pages/restaurant/ad_banners.html', context)


@staff_or_admin_required
def admin_ad_banner_toggle_status(request, banner_id):
    """
    Toggle ad banner active status (AJAX or regular POST)
    """
    if request.method == 'POST':
        banner = get_object_or_404(AdBanner, id=banner_id)
        banner.is_active = not banner.is_active
        banner.save()
        
        status_text = "activated" if banner.is_active else "deactivated"
        messages.success(request, f'Banner "{banner.title}" has been {status_text}.')
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({
                'success': True,
                'is_active': banner.is_active,
                'message': f'Banner {status_text} successfully'
            })
    
    return redirect('admin_ad_banner_list')


@staff_or_admin_required
def admin_ad_banner_delete(request, banner_id):
    """
    Delete an ad banner
    """
    if request.method == 'POST':
        banner = get_object_or_404(AdBanner, id=banner_id)
        banner_title = banner.title
        banner.delete()
        messages.success(request, f'Banner "{banner_title}" has been deleted successfully.')
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': True, 'message': 'Banner deleted successfully'})
    
    return redirect('admin_ad_banner_list')

# ============================
# End of Ad Banner Management
# ============================