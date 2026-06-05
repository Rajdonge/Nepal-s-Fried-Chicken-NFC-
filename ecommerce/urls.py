"""
URL configuration for ecommerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.views.generic import TemplateView
from . import views

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # Admin URLs
    path('admin/', admin.site.urls),
    path('admin-dashboard/',include('dashboard.urls')),

    # Main Pages
    path('home/',views.home_page,name="home"),
    path('search/',views.search_page,name='search'),
    path('all-collections/',views.all_collections,name="all_collections"),
    path("new-arrivals/",views.new_arrivals_page,name="new_arrivals"),
    path("restaurant_partner/",views.become_restaurant,name="restaurant_partner_page"),
    path("privacy-policy/",views.privacy_policy,name="privacy_policy"),

    # Restaurant & Menu Item URLs
    path("restaurants/",views.restaurants,name="restaurants"),
    path("restaurants/<slug:slug>/",views.restaurant_details,name="restaurant_details"),
    path('menu-item/<slug:slug>/',views.menu_item_details,name="menu_item_details"),
    path("cuisine/<slug:slug>/",views.cuisine_details,name='cuisine_details'),
    
    # Cart Management
    # path('cart/',views.carts,name="carts"),
    # path('api/cart/add/',views.add_to_cart,name="add_to_cart"),
    # path('api/cart/update/',views.update_cart_item,name="update_cart_item"),
    # path('api/cart/remove/',views.remove_from_cart,name="remove_from_cart"),
    
    # Checkout & Orders
    # path('checkout/', views.checkout, name='checkout_page'),
    # path('api/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    # path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    # Authentication URLs
    path("",views.login_page,name="login_page"),
    path("signup/",views.signup_page,name='signup_page'),
    path("forget-password/",views.forget_password,name="forget_password"),
    path('set-password',views.set_password_view,name="set_password"),
    path("logout",views.logout_view,name="logout"),
    path('contact/',views.contact_view,name='contact'),
    path('verify-otp/', views.verify_otp_page, name='verify_otp_page'),
    
    # Customer Dashboard
    path("customer-profile/",views.customer_profile,name='customer_profile'),
    path("dashboard/customer/edit/profile/",views.edit_profile,name='edit_profile'),
    path("dashboard/customer/orders/",views.customer_orders,name='customer_orders'),
    path("dashboard/customer/order/<str:order_number>/",views.customer_order_detail,name='customer_order_detail'),
    
    path("dashboard/customer/invoices/",views.customer_invoices,name='customer_invoices'),
    path('dashboard/customer/invoice/<str:invoice_number>/', views.customer_invoice_detail, name='customer_invoice_detail'),
    path('dashboard/<int:menu_item_id>/review/', views.write_menu_review, name='write_menu_review'),

    
    
    # API URLs
    path('api/', include('api.urls')),
    # PWA root-level assets (so service worker and manifest control whole site)
    path('service-worker.js', views.service_worker, name='service_worker'),
    path('manifest.json', views.web_manifest, name='web_manifest'),
    # Digital Asset Links: make assetlinks.json available at /.well-known/assetlinks.json
    path('.well-known/assetlinks.json', views.assetlinks, name='assetlinks'),

    path('login-with-token/', views.login_with_token, name='login_with_token'),

    
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
