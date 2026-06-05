from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.admin_dashboard, name='admin_dashboard'),

    # User Management
    path('users/', views.admin_users_list, name='admin_users_list'),
    # path('users/add/', views.admin_user_add, name='admin_user_add'),
    path('users/<int:pk>/update/', views.admin_user_update, name='admin_user_update'),
    path('users/<int:pk>/delete/', views.admin_user_delete, name='admin_user_delete'),

    # Staff Management
    path('staff-dashboard/', views.staff_dashboard, name='staff_dashboard'),
    
    path('staff/profile/', views.staff_profile_view, name='staff_profile'),
    
    
    # Staff management - admin
    path('users/staff/add/', views.admin_staff_add, name='admin_staff_add'),
    path('users/staff/', views.admin_staff_list, name='admin_staff_list'),
    path('users/staff/<int:pk>/edit/', views.admin_staff_edit, name='admin_staff_edit'),


    # Restaurant Management
    path('restaurants/', views.admin_restaurant_list, name='admin_restaurant_list'),
    path('restaurants/pending-kyc/', views.admin_restaurant_pending_kyc, name='admin_restaurant_pending_kyc'),
    path('restaurants/verified-kyc/', views.admin_restaurant_verified_kyc, name='admin_restaurant_verified_kyc'),
    path('restaurants/add/', views.admin_restaurant_add, name='admin_restaurant_add'),
    path('restaurants/<int:pk>/update/', views.admin_restaurant_update, name='admin_restaurant_update'),
    path('restaurants/<int:pk>/delete/', views.admin_restaurant_delete, name='admin_restaurant_delete'),
    path('restaurants/<int:pk>/change-status/', views.admin_restaurant_change_status, name='admin_restaurant_change_status'),
       
     #delivery person management
    path('delivery/', views.delivery_home, name='delivery_home'),
    path('delivery/dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/orders/', views.delivery_orders_list, name='delivery_orders_list'),
    path('delivery/orders/<int:assignment_id>/', views.delivery_order_detail, name='delivery_order_detail'),
    path('delivery/profile/', views.delivery_profile, name='delivery_profile'),
    



    # Delivery Person Management (Admin)
    path('delivery-persons/', views.admin_delivery_persons_list, name='admin_delivery_persons_list'),
    path('delivery-persons/create/', views.admin_delivery_person_create, name='admin_delivery_person_create'),
    path('delivery-persons/<int:pk>/edit/', views.admin_delivery_person_edit, name='admin_delivery_person_edit'),
    path('delivery-persons/<int:pk>/delete/', views.admin_delivery_person_delete, name='admin_delivery_person_delete'),

    # Delivery Assignments Management (Admin)
    path('delivery-assignments/', views.admin_delivery_assignments_list, name='admin_delivery_assignments_list'),
    path('delivery-assignments/assign/', views.admin_assign_order, name='admin_assign_order'),
    path('delivery-assignments/<int:assignment_id>/details/', views.admin_assignment_details, name='admin_assignment_details'),
    # Toggle Vendors VIsibility
    #  path('vendors/<int:pk>/toggle-visibility/', views.admin_vendor_toggle_visibility, name='admin_vendor_toggle_visibility'),

    
    # Payment Management
    path('payments/', views.admin_payments_overview, name='admin_payments_overview'),
    path('payments/restaurant/<int:restaurant_id>/', views.admin_restaurant_payments_detail, name='admin_restaurant_payments_detail'),

    # Commission
    path('admin/api/commission/update/', views.admin_update_commission, name='admin-update-commission'),

    # Payout Requests
    path('payout-requests/', views.admin_payout_requests_list, name='admin_payout_requests_list'),
    path('payout-requests/pending/', views.admin_payout_requests_pending, name='admin_payout_requests_pending'),
    path('payout-requests/rejected/', views.admin_payout_requests_rejected, name='admin_payout_requests_rejected'),
    path('payout-requests/<int:pk>/status/', views.admin_payout_request_change_status, name='admin_payout_request_change_status'),

    # MenuItems Management
    path('menuItems/', views.admin_menuItems_list, name='admin_menuItems_list'),
    path('menuItems/featured/', views.admin_menuItems_featured, name='admin_menuItems_featured'),
    path('menuItems/low-stock/', views.admin_menuItems_low_stock, name='admin_menuItems_low_stock'),
    path('menuItems/add/', views.admin_menuItem_add, name='admin_menuItem_add'),
    path('menuItems/<int:pk>/update/', views.admin_menuItem_update, name='admin_menuItem_update'),
    path('menuItems/<int:pk>/delete/', views.admin_menuItem_delete, name='admin_menuItem_delete'),
    

        # Menu Section Management
    path('menu-sections/', views.admin_menu_sections_list, name='admin_menu_sections_list'),
    path('menu-sections/add/', views.admin_menu_section_add, name='admin_menu_section_add'),
    path('menu-sections/<int:pk>/edit/', views.admin_menu_section_edit, name='admin_menu_section_edit'),
    path('menu-sections/<int:pk>/delete/', views.admin_menu_section_delete, name='admin_menu_section_delete'),
    # path('subcategories/<int:category_id>/', views.get_subcategories, name='get_subcategories'),
    # path('childcategories/<int:subcategory_id>/', views.get_childcategories, name='get_childcategories'),

    
    
    # Brand Management
    
    # path('brands/', views.admin_brand_list, name='admin_brand_list'),
    # path('brands/add/', views.admin_brand_add, name='admin_brand_add'),
    # path('brands/edit/<int:brand_id>/', views.admin_brand_update, name='admin_brand_update'),
    # path('brands/delete/<int:brand_id>/', views.admin_brand_delete, name='admin_brand_delete'),

    # Category Management
    # path('categories/', views.admin_categories_list, name='admin_categories_list'),
    # path('categories/add/', views.admin_category_add, name='admin_category_add'),
    # path('categories/<int:pk>/update/', views.admin_category_update, name='admin_category_update'),
    # path('categories/<int:pk>/delete/', views.admin_category_delete, name='admin_category_delete'),

    # SubCategory Management
    # path('subcategories/',views.admin_subcategory_list,name='admin_subcategory_list'),
    # path('subcategory/add/',views.admin_subcategory_add,name="admin_subcategory_add"),
    # path('subcategory/edit/<int:subcategory_id>/',views.admin_subcategory_update,name='admin_subcategory_update'),
    # path('subcategory/delete/<int:subcategory_id>/',views.admin_subcategory_delete,name='admin_subcategory_delete'),


    # path('child-categories/', views.admin_childcategory_list, name='admin_childcategory_list'),
    # path('child-categories/add/', views.admin_childcategory_add, name='admin_childcategory_add'),
    # path('child-categories/<int:childcategory_id>/edit/',views.admin_childcategory_update, name='admin_childcategory_update'),
    # path('child-categories/<int:childcategory_id>/delete/',views.admin_childcategory_delete,name='admin_childcategory_delete'),
    # path('ajax/get-childcategories/<int:subcategory_id>/', views.get_childcategories, name='get_childcategories'),

  
    
    # Order Management
    path('orders/', views.admin_orders_list, name='admin_orders_list'),
    path('odrer-details/<str:order_number>/',views.admin_order_details,name='admin_order_details'),
    path('orders/pending/', views.admin_orders_pending, name='admin_orders_pending'),
    path('orders/delivered/', views.admin_orders_delivered, name='admin_orders_delivered'),
    path('orders/<str:order_number>/items/', views.admin_order_items_json, name='admin_order_items_json'),
    path('orders/<str:order_number>/delete/', views.admin_order_delete, name='admin_order_delete'),
    
    path('orders/<str:order_number>/status/', views.admin_order_change_status, name='admin_order_change_status'),
    
    path('orders/<str:order_number>/invoice/',views.admin_order_invoice_view,name="admin_orders_invoice_list"),
    path('invoice/<str:invoice_number>/', views.admin_invoice_detail, name='admin_invoice_detail'),

    

    # Review Management
    path('reviews/', views.admin_reviews_list, name='admin_reviews_list'),
    path('reviews/add/', views.admin_review_add, name='admin_review_add'),
    path('reviews/<int:pk>/update/', views.admin_review_update, name='admin_review_update'),
    path('reviews/<int:pk>/delete/', views.admin_review_delete, name='admin_review_delete'),

    # Contact Management
    path('contacts/', views.admin_contacts_list, name='admin_contacts_list'),
    path('contacts/<int:pk>/delete/', views.admin_contact_delete, name='admin_contact_delete'),
    path('contacts/unread/',views.admin_contacts_unread,name="admin_contact_unread"),
    path('contacts/read/', views.admin_read_contact, name='admin_read_contacts'),

    # Shipping Cost Management
    path('tax-rate/', views.admin_tax_rate_view,name="admin_tax_rate"),
    path('tax-rate/edit/<int:id>/',views.admin_tax_rate_edit,name="admin_tax_rate_update"),
    
    
    # Newsletter Management
    path('newsletter/', views.admin_newsletter_list, name='admin_newsletter_list'),
    path('newsletter/add/', views.admin_newsletter_add, name='admin_newsletter_add'),
    path('newsletter/<int:pk>/update/', views.admin_newsletter_update, name='admin_newsletter_update'),
    path('newsletter/<int:pk>/delete/', views.admin_newsletter_delete, name='admin_newsletter_delete'),

    # Slider Management
    path('sliders/', views.admin_sliders_list, name='admin_sliders_list'),
    path('sliders/add/', views.admin_slider_add, name='admin_slider_add'),
    path('sliders/<int:pk>/update/', views.admin_slider_update, name='admin_slider_update'),
    path('sliders/<int:pk>/delete/', views.admin_slider_delete, name='admin_slider_delete'),

    # Banner Management
    path('banners/', views.admin_banners_list, name='admin_banners_list'),
    path('banners/add/', views.admin_banner_add, name='admin_banner_add'),
    path('banners/<int:pk>/update/', views.admin_banner_update, name='admin_banner_update'),
    path('banners/<int:pk>/delete/', views.admin_banner_delete, name='admin_banner_delete'),

   
    # Coupon Management
    path('coupons/', views.admin_coupons_list, name='admin_coupons_list'),
    path('coupons/add/', views.admin_coupon_add, name='admin_coupon_add'),
    path('coupons/<int:pk>/update/', views.admin_coupon_update, name='admin_coupon_update'),
    path('coupons/<int:pk>/delete/', views.admin_coupon_delete, name='admin_coupon_delete'),

 
    # Organization Management
    path('organization/', views.admin_organization_view, name='admin_organization_view'),
    path('organization/update/', views.admin_organization_update, name='admin_organization_update'),

    # Notification Management
    path('notifications/', views.admin_notifications_list, name='admin_notifications_list'),
    path('notifications/add/', views.admin_notification_add, name='admin_notification_add'),
    path('notifications/<int:pk>/update/', views.admin_notification_update, name='admin_notification_update'),
    path('notifications/<int:pk>/delete/', views.admin_notification_delete, name='admin_notification_delete'),
    
    
    # Profile Management
    path('profile/',views.admin_profile_view,name="admin_profile"),
    path('profile/update/',views.admin_profile_edit,name="admin_profile_edit"),
    
    # Change Password
    path('change-password/',views.change_password_view,name="change_password"),
    
    
    # =================================
    #   Restaurant
    # =================================
    path('restaurant-dashboard/', views.restaurant_dashboard, name='restaurant_dashboard'),
    path('restaurant/menu-items/', views.restaurant_menu_items_list, name='restaurant_menu_items_list'),
    path('restaurant/menu-items/add/', views.restaurant_menu_item_add, name='restaurant_menu_item_add'),
    path('restaurant/menu-items/<int:pk>/update/', views.restaurant_menu_item_update, name='restaurant_menu_item_update'),
    path('restaurant/menu-items/<int:pk>/delete/', views.restaurant_menu_item_delete, name='restaurant_menu_item_delete'),
    path('restaurant/menu-items/unavailable/', views.restaurant_menu_items_unavailable, name='restaurant_menu_items_unavailable'),
    # Restaurant Menu Section Management
    path('restaurant/menu-sections/', views.restaurant_menu_sections_list, name='restaurant_menu_sections_list'),
    path('restaurant/menu-sections/add/', views.restaurant_menu_section_add, name='restaurant_menu_section_add'),

    path('restaurant/orders/', views.restaurant_orders_list, name='restaurant_orders_list'),
    path('restaurant/order-details/<str:order_number>/',views.restaurant_order_details,name="restaurant_order_details"),
    path('restaurant/orders/pending/', views.restaurant_orders_pending, name='restaurant_orders_pending'),
    path('restaurant/orders/delivered/', views.restaurant_orders_delivered, name='restaurant_orders_delivered'),
    path('restaurant/orders/<str:order_number>/invoice/',views.restaurant_order_invoice_view,name="restaurant_orders_invoice_list"),
    path('orders/payment/<str:order_number>/status/',views.restaurant_order_update_payment_status,name="restaurant_payment_change_status"),    
    
    # restaurant/urls.py
    path('orders/<str:order_number>/change-status/', views.restaurant_order_change_status, name='restaurant_order_change_status'),

    path('restaurant/payout-lists/', views.restaurant_payouts_list, name='restaurant_payout_list'),
    path('restaurant/payout-requests/add/', views.restaurant_payout_request_add, name='restaurant_payout_requests_add'),
    path('restaurant/payouts/pending/', views.restaurant_payout_requests_pending, name='restaurant_pending_payout'),
    path('restaurant/payouts/rejected/', views.restaurant_payout_requests_rejected, name='restaurant_rejected_payout'),
    
    

    path('restaurant/wallet/', views.restaurant_wallet_view, name='restaurant_wallet_view'),
    
    
    # Review
    path('restaurant/menu-item-reviews/', views.restaurant_menu_item_reviews_list, name='restaurant_menu_item_reviews_list'),

    # Invoice
    path('restaurant/invoice/',views.restaurant_invoices,name="restaurant_invoices_list"),
    path('restaurant/invoice-details/<str:invoice_number>/',views.restaurant_invoice_detail,name='restaurant_invoice_detail'),
    
    #Restaurant Profile 
    path('restaurant/profile/',views.restaurant_profile_view,name='restaurant_profile'),
    path('restaurant/profile/edit/', views.restaurant_profile_edit_view, name='restaurant_edit_profile'),
    
    # Resubmit Kyc
    path('restaurant/kyc/resubmit/',views.restaurant_resubmit_kyc,name="restaurant_kyc_resubmit"),

    # Admin Ad Banner Management
    path('ad-banners/', views.admin_ad_banner_list, name='admin_ad_banner_list'),
    path('ad-banners/create/', views.admin_create_or_edit_ad_banner, name='admin_create_ad_banner'),
    path('ad-banners/<int:banner_id>/edit/', views.admin_create_or_edit_ad_banner, name='admin_edit_ad_banner'),
    path('ad-banners/<int:banner_id>/toggle/', views.admin_ad_banner_toggle_status, name='admin_ad_banner_toggle'),
    path('ad-banners/<int:banner_id>/delete/', views.admin_ad_banner_delete, name='admin_ad_banner_delete'),
    
]
    
    
