from django.contrib import admin
from .models import *

# Register all models
# User Management
admin.site.register(UserRole)
admin.site.register(UserProfile)
admin.site.register(StaffProfile)
admin.site.register(DeliveryPerson)
admin.site.register(DeliveryAssignment)

# Restaurant Management (formerly Vendor)
admin.site.register(Restaurant)
admin.site.register(RestaurantCommission)
admin.site.register(RestaurantPayoutRequest)
admin.site.register(RestaurantWallet)
admin.site.register(DeliveryZone)
admin.site.register(RestaurantTiming)

# Menu Management (formerly Product)
admin.site.register(CuisineType)
admin.site.register(MenuSection)
admin.site.register(MenuItem)
admin.site.register(MenuItemImage)
admin.site.register(MenuItemOption)
admin.site.register(FoodTag)

# Order Management
admin.site.register(Cart)
admin.site.register(Address)
admin.site.register(Order)
admin.site.register(OrderItem)

# Reviews & Ratings
admin.site.register(RestaurantReview)

# Coupons & Payments
admin.site.register(Coupon)
admin.site.register(CouponUsage)
admin.site.register(TaxRate)
admin.site.register(Invoice)

# Platform Configuration
admin.site.register(Organization)
admin.site.register(Newsletter)
admin.site.register(Contact)
admin.site.register(Notification)
admin.site.register(Slider)
admin.site.register(Banner)
admin.site.register(OTPVerification)
