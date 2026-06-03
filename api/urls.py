from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView




# ==========================
#  Mobile App API URLs
# ==========================

urlpatterns = [
    
    path('register/', views.SignupAPIView.as_view()),
    path('verify-otp/', views.VerifySignupOTPAPIView.as_view()),
    path('resend-otp/', views.ResendSignupOTPAPIView.as_view()),
    path('login/', views.SignupLoginAPIView.as_view()),
    
    # Authentication APIs
    path('logout/', views.LogoutView.as_view()),
    path('forget-password/', views.ForgetPasswordApiView.as_view()),
    path('forget-password/verify-otp/', views.ForgetPasswordVerifyOtpApiView.as_view()),
    path('reset-password/', views.ResetPasswordApiView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    
    
   
    # Category APIs
    path('categories/', views.CategoryApiView.as_view()),
    
    # Pages APIs
    # path('home/', views.HomeApiView.as_view()),
    path('all-collections/', views.AllCollectionsApiView.as_view()),
    path('new-arrivals/', views.NewArrivalsApiView.as_view()),
    path('vendors/', views.VendorsApiView.as_view()),
    
    path('filter-products/', views.FilterProductsApiView.as_view()),
    path('search-products/', views.SearchProductsApiView.as_view()),
    
    
    # Details APIs
    path('vendor/<int:vendor_id>/', views.VendorProductsDetails.as_view()),
    path('product/<int:id>/', views.ProductDetailsApiView.as_view()),
    path('category/<int:category_id>/products/', views.CategoryProductsApiView.as_view()),
    # path('subcategory/<int:subcategory_id>/products/', views.SubCategoryProductsApiView.as_view()),
    
    
    
    # Cart APIs
    # path('cart/', views.ViewCartApiView.as_view()),
    # path('cart-add/', views.AddToCartApiView.as_view()),
    # path('cart-update/', views.UpdateCartItemApiView.as_view()),
    # path('cart-remove/', views.RemoveFromCartApiView.as_view()),
    
    # profile APIs
    path('customer-profile/', views.CustomerProfileApiView.as_view()),
    path('edit-profile/', views.EditCustomerProfileApiView.as_view()),
    path('customer-orders/', views.CustomerOrderHistoryApiView.as_view()),
    path('customer-order/<str:order_id>/', views.CustomerOrderDetailsApiView.as_view()),
    path('change-password/', views.ChangePasswordApiView.as_view()),
    
    
   
    # Checkout API
    path('checkout/', views.CheckoutApiView.as_view()),

    # Review APIs
    path('product/<int:product_id>/reviews/', views.ProductReviewsApiView.as_view()),

    # Coupon API
    path('coupon/verify/', views.CouponVerifyApiView.as_view()),

    # Newsletter API
    path('newsletter/subscribe/', views.NewsletterApiView.as_view()),

    # Contact API
    path('contact/', views.ContactApiView.as_view()),

    # Notification API
    path('notifications/', views.NotificationApiView.as_view()),



    #Delivery API
    path('delivery-login/', views.DeliveryLoginApiView.as_view() ),
    path('delivery-logout/', views.DeliveryLogoutApiView.as_view() ),
    path('delivery-profile/', views.DeliveryProfileApiView.as_view() ),
    path('delivery-profile/update/', views.UpdateDeliveryProfileApiView.as_view() ),
    path('delivery-assignments/', views.DeliveryAssignmentsListApiView.as_view() ),
    path('delivery-assignments/<int:assignment_id>/', views.DeliveryAssignmentDetailApiView.as_view() ),
    path('delivery-assignments/<int:assignment_id>/update-status/', views.UpdateAssignmentStatusApiView.as_view()),
    path('delivery-assignments/<int:assignment_id>/upload-photo/', views.UploadDeliveryPhotoApiView.as_view() ),
    path('delivery-dashboard/', views.DeliveryDashboardApiView.as_view()),



      # Restaurant & Food Delivery APIs
    path('restaurants/', views.RestaurantListApiView.as_view()),
    path('restaurant/<int:restaurant_id>/', views.RestaurantDetailsApiView.as_view()),
    path('restaurant/<int:restaurant_id>/menu/', views.RestaurantMenuApiView.as_view()),
    path('food-cart/add/', views.AddMenuItemToCartApiView.as_view()),
        
    path('login-via-ecommerce-token/', views.login_via_ecommerce_token),


    # API URLS
    path('restaurants/list/', views.RestaurantsView.as_view(), name='restaurant-list'),
    path('restaurant/<slug:slug>/', views.RestaurantDetailView.as_view(), name='restaurant-detail'),
    path('restaurant/<slug:restaurant_slug>/menu-sections/', views.RestaurantMenuSectionsView.as_view(), name='restaurant-menu-sections'),
    path('restaurants/menu-sections/', views.RestaurantsMenuSectionsView.as_view(), name='restaurant-menu-sections'),
    path('restaurant/<slug:restaurant_slug>/menu-items/', views.RestaurantMenuItem.as_view(), name='restaurant-menu-items'),
    path('restaurants/menu-items/', views.RestaurantsMenuItemsView.as_view(), name='restaurants-menu-items'),
    path('menu-item/<int:menu_item_id>/', views.MenuItemDetailsApiView.as_view()),

    path('home/', views.HomePage_APIView.as_view(), name='home'),
    path('menus/', views.RestaurantMenuAPIView.as_view(), name='restaurant-menu'),
    
    # cart API urls
    path('cart/add/', views.AddToCartView.as_view(), name='add-to-cart'),
    path('cart/', views.ViewCartView.as_view(), name='view-cart'),
    path('cart/update/<int:cart_item_id>/', views.UpdateCartItemView.as_view(), name='update-cart'),
    path('cart/remove/<int:cart_item_id>/', views.RemoveFromCartView.as_view(), name='remove-from-cart'),
    path('cart/clear/', views.ClearCartView.as_view(), name='clear-cart'),
    path('cart/merge/', views.MergeGuestCartView.as_view(), name='merge-cart'),
    
    # User Profile API (for checkout pre-fill)
    path('user/profile/', views.GetUserProfileView.as_view(), name='api-user-profile'),

    # Address Management URLs
    path('addresses/', views.AddressListCreateView.as_view(), name='address-list-create'),
    path('addresses/<int:address_id>/', views.AddressDetailView.as_view(), name='address-detail'),
    path('addresses/<int:address_id>/set-default/', views.SetDefaultAddressView.as_view(), name='address-set-default'),
    path('user/addresses/', views.GetUserAddressesView.as_view(), name='user-addresses'),
    
    # Order API URLs
    path('calculate-delivery/', views.CalculateDeliveryAPIView.as_view(), name='calculate_delivery'),
    path('orders/create/', views.CreateOrderView.as_view(), name='api-create-order'),
    path('orders/my-orders/', views.UserOrdersView.as_view(), name='api-user-orders'),
    path('orders/guest-lookup/', views.GuestOrderLookupView.as_view(), name='api-guest-order-lookup'),
    path('orders/<identifier>/', views.OrderDetailView.as_view(), name='api-order-detail'),
    path('orders/<int:order_id>/cancel/', views.CancelOrderView.as_view(), name='api-cancel-order'),
]