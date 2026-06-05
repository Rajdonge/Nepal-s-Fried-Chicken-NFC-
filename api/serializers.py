from rest_framework import serializers
from dashboard.models import (
    Restaurant,
    MenuSection, 
    MenuItemImage, 
    MenuItem,
    RestaurantReview,
    AdBanner,
    MenuItemReview,
    Cart,
    Order, 
    OrderItem,
    Address,
)

class RestaurantSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    class Meta:
        model = Restaurant
        fields = [
            'id', 'restaurant_name', 'slug', 'logo', 'banner', 'description', 
            'phone', 'address', 'city', 'province', 'rating', 'average_rating', 'reviews_count', 'qr_image', 'is_open']
        
    def get_average_rating(self, obj):
        """Calculate average rating from restaurant reviews"""
        return round(float(obj.get_average_rating()), 1)
    
    def get_reviews_count(self, obj):
        """Get total number of reviews"""
        return obj.reviews.count()
    

class RestaurantMenuItemImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = MenuItemImage
        fields = ['id', 'image_url', 'order']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class RestaurantsMenuItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    images = RestaurantMenuItemImageSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'image_url', 'images', 'is_vegetarian', 'is_available',
            'is_featured', 'prep_time', 'average_rating', 'reviews_count'
        ]
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews.exists():
            return round(float(sum(r.rating for r in reviews) / reviews.count()), 1)
        return 0
    
    def get_reviews_count(self, obj):
        return obj.reviews.count()

class RestaurantsMenuSectionSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    class Meta:
        model = MenuSection
        fields = ['id', 'name', 'description', 'image_url', 'items_count', 'items', 'order']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_items_count(self, obj):
        return obj.menu_items.filter(is_available=True).count()
    
    def get_items(self, obj):
        items = obj.menu_items.filter(is_available=True).order_by('id')
        return RestaurantsMenuItemSerializer(items, many=True, context=self.context).data

        
# Home Serializers

from django.utils.html import strip_tags

class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer for menu items"""

    average_rating = serializers.FloatField(read_only=True)
    image = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'price',
            'image',
            'is_vegetarian',
            'prep_time',
            'is_available',
            'is_featured',
            'average_rating',
            'views_count'
        ]

    def get_description(self, obj):
        if obj.description:
            return strip_tags(obj.description).replace('\r', '').replace('\n', ' ').strip()
        return ""

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class MenuSectionSerializer(serializers.ModelSerializer):
    """Serializer for menu sections with their items"""
    menu_items = MenuItemSerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuSection
        fields = ['id', 'name', 'description', 'image', 
                  'order', 'is_active', 'menu_items']
    
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class AdBannerSerializer(serializers.ModelSerializer):
    """Serializer for advertisement banners"""
    image = serializers.SerializerMethodField()
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = AdBanner
        fields = ['id', 'title', 'description', 'image', 
                  'link_url', 'cta_text', 'order', 'is_active', 
                  'is_valid', 'clicks', 'impressions']
    
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class RestaurantReviewSerializer(serializers.ModelSerializer):
    """Serializer for restaurant reviews"""
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantReview
        fields = ['id', 'user_name', 'user_avatar', 'rating', 'comment', 
                  'food_quality_rating', 'delivery_rating', 'created_at']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    
    def get_user_avatar(self, obj):
        if hasattr(obj.user, 'profile') and obj.user.profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.profile.avatar.url)
            return obj.user.profile.avatar.url
        return None

class RestaurantSerializer(serializers.ModelSerializer):
    """Serializer for restaurant details"""
    logo = serializers.SerializerMethodField()
    banner = serializers.SerializerMethodField()
    rating = serializers.DecimalField(max_digits=3, decimal_places=1, read_only=True)
    recent_reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Restaurant
        fields = [
            'id', 'restaurant_name', 'slug', 'logo', 'banner', 
            'description', 'phone', 'address', 'city', 'province', 
            'cuisines', 'min_order_value', 'delivery_fee', 
            'avg_prep_time', 'rating', 'is_active', 'is_open',
            'recent_reviews'
        ]
    
    def get_logo(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None
    
    def get_banner(self, obj):
        if obj.banner:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.banner.url)
            return obj.banner.url
        return None
    
    def get_recent_reviews(self, obj):
        """Get 5 most recent reviews"""
        reviews = obj.reviews.all()[:5]
        return RestaurantReviewSerializer(reviews, many=True, context=self.context).data

class HomePageDataSerializer(serializers.Serializer):
    """Serializer for home page data"""
    restaurant = RestaurantSerializer()
    explore_menu_sections = MenuSectionSerializer(many=True)
    ad_banners = AdBannerSerializer(many=True)
    favorite_menu_items = MenuItemSerializer(many=True)


# Explore Menu page Serializers

class MenuItemReviewSerializer(serializers.ModelSerializer):
    """Serializer for menu item reviews"""
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItemReview
        fields = ['id', 'user_name', 'rating', 'comment', 'created_at']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer for menu items with all details"""
    average_rating = serializers.FloatField(read_only=True)
    image = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'slug', 'description', 'price',
            'image', 'is_vegetarian', 'prep_time',
            'is_available', 'is_featured', 'is_favorite',
            'average_rating', 'views_count', 'recent_reviews', 'created_at'
        ]
    
    def get_description(self, obj):
        """Strip HTML tags from CKEditor content"""
        if obj.description:
            return strip_tags(obj.description).replace('\r', '').replace('\n', ' ').strip()
        return ""
    
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_recent_reviews(self, obj):
        """Get 3 most recent reviews for this menu item"""
        reviews = obj.reviews.all()[:3]
        return MenuItemReviewSerializer(reviews, many=True, context=self.context).data

class MenuSectionSerializer(serializers.ModelSerializer):
    """Serializer for menu sections with their items"""
    menu_items = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuSection
        fields = ['id', 'name', 'description', 'image', 'order', 'is_active', 'menu_items']
    
    def get_description(self, obj):
        """Strip HTML tags from CKEditor content for menu section description"""
        if obj.description:
            return strip_tags(obj.description).replace('\r', '').replace('\n', ' ').strip()
        return ""
    
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_menu_items(self, obj):
        """Get only available menu items for this section"""
        items = obj.menu_items.filter(is_available=True).order_by('-is_featured', '-created_at')
        return MenuItemSerializer(items, many=True, context=self.context).data

class RestaurantMenuSerializer(serializers.ModelSerializer):
    """Serializer for restaurant with menu sections"""
    logo = serializers.SerializerMethodField()
    banner = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    menu_sections = serializers.SerializerMethodField()
    
    class Meta:
        model = Restaurant
        fields = [
            'id', 'restaurant_name', 'slug', 'logo', 'banner', 'description',
            'phone', 'address', 'city', 'province', 
            'avg_prep_time', 'rating', 'is_active', 'is_open',
            'menu_sections'
        ]
    
    def get_description(self, obj):
        """Strip HTML tags from CKEditor content for restaurant description"""
        if obj.description:
            return strip_tags(obj.description).replace('\r', '').replace('\n', ' ').strip()
        return ""
    
    def get_logo(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None
    
    def get_banner(self, obj):
        if obj.banner:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.banner.url)
            return obj.banner.url
        return None
    
    def get_menu_sections(self, obj):
        """Get all active menu sections with their items"""
        sections = obj.menu_sections.filter(is_active=True).order_by('order')
        return MenuSectionSerializer(sections, many=True, context=self.context).data
        
# Cart Serializers
class AddToCartSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

class CartItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_price = serializers.DecimalField(source='menu_item.price', read_only=True, max_digits=10, decimal_places=2)
    menu_item_image = serializers.SerializerMethodField()
    item_total = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'menu_item', 'menu_item_name', 'menu_item_price', 'menu_item_image', 
                  'quantity', 'item_total']
    
    def get_menu_item_image(self, obj):
        request = self.context.get('request')
        if obj.menu_item.image and request:
            return request.build_absolute_uri(obj.menu_item.image.url)
        return None
    
    def get_item_total(self, obj):
        """Get total price from the property"""
        return float(obj.total_price)
        
        
        
# Order Serializers
class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_image = serializers.SerializerMethodField()
    item_total = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'menu_item', 'menu_item_name', 'menu_item_image',
            'quantity', 'price', 'item_total'
        ]
    
    def get_menu_item_image(self, obj):
        if obj.menu_item and obj.menu_item.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.menu_item.image.url)
            return obj.menu_item.image.url
        return None
    
    def get_item_total(self, obj):
        """Calculate total for this line item"""
        return float(obj.get_total())
    

class OrderSerializer(serializers.ModelSerializer):
    """Main Order serializer with full details"""
    items = OrderItemSerializer(many=True, read_only=True)
    
    # Customer info
    customer_name = serializers.SerializerMethodField()
    
    # Status displays
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    # Calculated fields
    can_cancel = serializers.BooleanField(read_only=True)
    can_request_refund = serializers.BooleanField(read_only=True)
    
    # Formatted amounts
    subtotal_formatted = serializers.SerializerMethodField()
    total_formatted = serializers.SerializerMethodField()
    
    # Delivery location
    has_valid_location = serializers.SerializerMethodField()
    delivery_coordinates = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'payment_method', 'payment_method_display',
            'payment_status', 'payment_status_display',
            'created_at', 'updated_at', 'delivered_at', 'cancelled_at',
            
            # Customer info
            'full_name', 'phone', 'email', 'address', 'city', 'province', 'postal_code',
            'customer_name',
            
            # Delivery Location
            'delivery_latitude', 'delivery_longitude', 'delivery_distance_km',
            'has_valid_location', 'delivery_coordinates',
            
            # Pricing
            'subtotal', 'subtotal_formatted',
            'discount', 'tax_percentage',
            'total', 'total_formatted',
            
            # Related objects
            'items',
            
            # Actions
            'can_cancel', 'can_request_refund',
        ]
    
    def get_customer_name(self, obj):
        return obj.customer_display_name
    
    def get_subtotal_formatted(self, obj):
        return f"Rs {float(obj.subtotal):,.2f}"
    
    def get_total_formatted(self, obj):
        return f"Rs {float(obj.total):,.2f}"
    
    def get_has_valid_location(self, obj):
        return obj.has_valid_delivery_location()
    
    def get_delivery_coordinates(self, obj):
        coords = obj.get_delivery_coordinates()
        if coords:
            return {
                'latitude': coords[0],
                'longitude': coords[1]
            }
        return None


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified Order serializer for list views"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    total_formatted = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    has_valid_location = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'payment_status', 'payment_status_display',
            'created_at', 'total', 'total_formatted', 'item_count',
            'delivery_latitude', 'delivery_longitude', 'has_valid_location'
        ]
    
    def get_total_formatted(self, obj):
        return f"Rs {float(obj.total):,.2f}"
    
    def get_item_count(self, obj):
        return obj.items.count()
    
    def get_has_valid_location(self, obj):
        return obj.has_valid_delivery_location()


class UserProfileSerializer(serializers.Serializer):
    """Serializer for logged-in user profile data"""
    full_name = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField()
    address = serializers.CharField()
    city = serializers.CharField()
    province = serializers.CharField()
    # Optional delivery location fields
    delivery_latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    delivery_longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)


from decimal import Decimal
class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating a new order"""
    # Address selection (for authenticated users)
    address_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID of saved address to use for delivery"
    )
    
    # Shipping info
    full_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(  # NEW: For plus codes / location string
        max_length=500, 
        required=False, 
        allow_blank=True,
        help_text="Location string like 'M88R+HPR, Imadol, Bagmati Province'"
    )
    landmark = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    district = serializers.CharField(max_length=100, required=False, allow_blank=True)
    province = serializers.CharField(max_length=50, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=10, required=False, allow_blank=True)
    
    # Delivery location
    delivery_latitude = serializers.FloatField(required=False, allow_null=True)
    delivery_longitude = serializers.FloatField(required=False, allow_null=True)
    
    # Payment
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_CHOICES, default='cod')
    
    # Address saving options (for authenticated users)
    save_as_address = serializers.BooleanField(
        required=False, 
        default=False,
        help_text="Save this address to your account"
    )
    address_type = serializers.CharField(
        max_length=20, 
        required=False, 
        default='home',
        help_text="home, office, or other"
    )
    set_as_default = serializers.BooleanField(
        required=False, 
        default=False,
        help_text="Set this as default address"
    )
    
    # Checkout options
    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Array of cart item IDs for specific checkout"
    )
    cart_item_id = serializers.IntegerField(
        required=False,
        help_text="Single cart item ID for buy now"
    )
    
    def validate(self, data):
        request = self.context.get('request')
        is_authenticated = request and request.user.is_authenticated
        
        # Check if either address_id OR manual address is provided
        address_id = data.get('address_id')
        has_manual_address = any([
            data.get('full_name'),
            data.get('phone'),
            data.get('address') or data.get('location')
        ])
        
        if not address_id and not has_manual_address:
            raise serializers.ValidationError({
                'non_field_errors': 'Either provide address_id or manual shipping information'
            })
        
        # Validate address_id if provided
        if is_authenticated and address_id:
            try:
                address = request.user.addresses.get(id=address_id)
                # If using saved address, we don't need to validate shipping fields
                # as they will be populated from the address
                return data
            except Address.DoesNotExist:
                raise serializers.ValidationError({
                    'address_id': f'Address with ID {address_id} not found'
                })
        
        # Validate manual address fields
        if not address_id:
            # For guest checkout, require essential fields
            if not is_authenticated:
                required_fields = ['full_name', 'phone', 'email']
                missing_fields = []
                
                for field in required_fields:
                    if not data.get(field):
                        missing_fields.append(field)
                
                # At least one of address or location is required
                if not data.get('address') and not data.get('location'):
                    missing_fields.append('address or location')
                
                if missing_fields:
                    raise serializers.ValidationError({
                        'message': f'For guest checkout, these fields are required: {", ".join(missing_fields)}',
                        'missing_fields': missing_fields
                    })
            
            # For authenticated users without address_id, validate essential fields
            if is_authenticated and not address_id:
                if not data.get('full_name') and not data.get('address') and not data.get('location'):
                    raise serializers.ValidationError({
                        'message': 'Please provide shipping information or select a saved address.'
                    })
        
        # Validate address_type if saving
        if data.get('save_as_address') and data.get('address_type'):
            address_type = data.get('address_type').lower()
            valid_choices = ['home', 'office', 'other']
            if address_type not in valid_choices:
                raise serializers.ValidationError({
                    'address_type': f'Invalid address type. Valid choices: {", ".join(valid_choices)}'
                })
            data['address_type'] = address_type
        
        # Validate coordinates
        if data.get('delivery_latitude') is not None:
            data['delivery_latitude'] = Decimal(
                f"{float(data['delivery_latitude']):.7f}"
            )
            lat = float(data['delivery_latitude'])
            if lat < -90 or lat > 90:
                raise serializers.ValidationError({
                    'delivery_latitude': 'Latitude must be between -90 and 90'
                })

        if data.get('delivery_longitude') is not None:
            data['delivery_longitude'] = Decimal(
                f"{float(data['delivery_longitude']):.7f}"
            )
            lng = float(data['delivery_longitude'])
            if lng < -180 or lng > 180:
                raise serializers.ValidationError({
                    'delivery_longitude': 'Longitude must be between -180 and 180'
                })
        
        # Validate phone number if provided
        if data.get('phone'):
            phone = data['phone']
            if len(phone) < 10:
                raise serializers.ValidationError({
                    'phone': 'Phone number must be at least 10 digits'
                })
        
        # Validate checkout options
        cart_item_ids = data.get('cart_item_ids', [])
        cart_item_id = data.get('cart_item_id')
        
        if cart_item_ids and cart_item_id:
            raise serializers.ValidationError({
                'non_field_errors': 'Cannot specify both cart_item_ids and cart_item_id'
            })
        
        return data
    

# Address Serializers
class AddressSerializer(serializers.ModelSerializer):
    """Serializer for Address model"""
    address_type_display = serializers.CharField(source='get_address_type_display', read_only=True)
    has_coordinates = serializers.SerializerMethodField()
    
    class Meta:
        model = Address
        fields = [
            'id', 'user', 'address_type', 'address_type_display',
            'full_name', 'phone', 'location', 'landmark', 'city',
            'district', 'province', 'postal_code', 'latitude', 'longitude',
            'is_default', 'has_coordinates', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_has_coordinates(self, obj):
        return obj.latitude is not None and obj.longitude is not None


class CreateAddressSerializer(serializers.ModelSerializer):
    # Override address_type to accept any case
    address_type = serializers.CharField(max_length=20)
    
    class Meta:
        model = Address
        fields = [
            'address_type', 'full_name', 'phone', 'location',
            'landmark', 'city', 'district', 'province', 'postal_code', 
            'latitude', 'longitude', 'is_default'
        ]
    
    def validate_address_type(self, value):
        """Convert to lowercase and validate against choices"""
        value = value.lower()
        
        # Check if the lowercase value is in the choices
        valid_choices = [choice[0] for choice in Address.ADDRESS_TYPES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"'{value}' is not a valid choice. Valid choices are: {', '.join(valid_choices)}")
        
        return value
    
    def validate_phone(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits")
        return value
    
    def validate(self, data):
        user = self.context['request'].user
        address_type = data.get('address_type')
        instance = getattr(self, 'instance', None)
        
        # Validate unique address type
        if not instance and Address.objects.filter(user=user, address_type=address_type).exists():
            raise serializers.ValidationError({
                "address_type": f"You already have a {address_type} address."
            })
        
        if instance and address_type and address_type != instance.address_type:
            if Address.objects.filter(user=user, address_type=address_type).exists():
                raise serializers.ValidationError({
                    "address_type": f"You already have a {address_type} address."
                })
        
        return data
    
    def create(self, validated_data):
        # Remove user from validated_data if it exists
        validated_data.pop('user', None)
        
        # Create address with user from context
        return Address.objects.create(
            user=self.context['request'].user,
            **validated_data
        )