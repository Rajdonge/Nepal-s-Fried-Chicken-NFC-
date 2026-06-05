from dashboard.models import Cart, CuisineType, Organization, RestaurantPayoutRequest, Restaurant, Order, MenuSection
from django.db.models import Prefetch

def global_context(request):
    """
    Provides cart item count and active categories globally.
    Works for both authenticated and guest users.
    """
    subcat_qs = MenuSection.objects.filter(is_active=True).prefetch_related('child_categories')
    categories = CuisineType.objects.filter(is_active=True).order_by('order', 'name')\
    .prefetch_related(Prefetch('subcategories', queryset=subcat_qs))
    
    cart_count = 0
    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(user=request.user)
        cart_count = sum(item.quantity for item in cart_items)
    else:
        # Try to get guest_id from session
        guest_id = request.session.get('guest_id')
        if guest_id:
            cart_items = Cart.objects.filter(guest_id=guest_id, user__isnull=True)
            cart_count = sum(item.quantity for item in cart_items)
    
    organization = Organization.objects.first()
    total_pending_payouts = RestaurantPayoutRequest.objects.filter(status='pending').count()
    
    # Restaurant 
    total_restaurant_pending_orders = 0
    total_restaurant_pending_payouts = 0
    user_role = getattr(request.user, 'role', None)
    if request.user.is_authenticated and user_role and user_role.role == 'restaurant':
        try:
            restaurant = Restaurant.objects.get(user=request.user)
            total_restaurant_pending_payouts = RestaurantPayoutRequest.objects.filter(restaurant=restaurant, status="pending").count()
            total_restaurant_pending_orders = Order.objects.filter(items__menu_item__restaurant=restaurant, status='pending').count()
        except Restaurant.DoesNotExist:
            pass

    return {
        'cart_count': cart_count,
        'categories': categories,
        'organization': organization,
        'total_pending_payouts': total_pending_payouts,
        'total_restaurant_pending_orders': total_restaurant_pending_orders,
        'total_restaurant_pending_payouts': total_restaurant_pending_payouts,
    }



import json
import os
from django.conf import settings

def nepal_locations(request):
    file_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'nepal_provinces.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {
        'nepal_locations': data
    }
