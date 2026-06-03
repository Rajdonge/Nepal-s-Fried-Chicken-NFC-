from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from django.core.validators import FileExtensionValidator, MinValueValidator
from decimal import Decimal
  
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

# ==================================
#   OTP Verification
# ==================================

class OTPVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,null=True,blank=True)
    otp_code = models.CharField(max_length=6,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OTP for {self.user.email}"
    
# -------------------------
# User Role Management
# -------------------------
class UserRole(models.Model):
    """Define user roles in the system"""
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('restaurant', 'Restaurant'),  # Food delivery system
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('delivery', 'Delivery Person'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='role',null=True,blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def is_customer(self):
        return self.role == 'customer'
    
    def is_restaurant(self):
        return self.role == 'restaurant'
    
    def is_vendor(self):  # Backward compatibility
        return self.role == 'restaurant'
    
    def is_admin(self):
        return self.role == 'admin'

#staff profile
class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    district = models.CharField(max_length=100)   # or use FK to District later
    created_at = models.DateTimeField(auto_now_add=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    citizenship = models.CharField(max_length=50, blank=True, null=True)
    citizenship_front = models.ImageField(upload_to='staffdata/citizenship/', blank=True, null=True)
    citizenship_back = models.ImageField(upload_to='staffdata/citizenship/', blank=True, null=True)
    photo = models.ImageField(upload_to='staffdata/photos/', blank=True, null=True)
    father_name = models.CharField(max_length=150, blank=True, null=True)
    grandfather_name = models.CharField(max_length=150, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    


    def __str__(self):
        return f"{self.user.username} - {self.district}"

# -------------------------
# User Management
# -------------------------
class UserProfile(models.Model):
    GENDER_CHOICES=( ('male','Male'),
                    ('female','Female'))
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name="profile")
    phone = models.CharField(max_length=15,null=True,blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    gender=models.CharField(max_length=10,choices=GENDER_CHOICES,null=True,blank=True)
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    province = models.CharField(max_length=50, null=True, blank=True)
    
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_role(self):
        """Get user role"""
        try:
            return self.user.role.get_role_display()
        except:
            return 'No Role Assigned'

# -------------------------
# Delivery Management
# -------------------------
class DeliveryPerson(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_person')
    
    district = models.CharField(max_length=100, default='')

    # Contact Info
    phone = models.CharField(max_length=15)
    address = models.TextField()
    

    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.phone}"    



class DeliveryAssignment(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    delivery_photo = models.ImageField(
        upload_to='delivery_photos/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Photo proof of delivery"
    )
    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='delivery_assignment')
    delivery_person = models.ForeignKey(DeliveryPerson, on_delete=models.CASCADE, related_name='assignments')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    
    # Timestamps for tracking
    assigned_at = models.DateTimeField(auto_now_add=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    in_transit_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Failure tracking
    failure_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.delivery_person.user.first_name}"

# -------------------------
# Restaurant Management (Food Delivery)
# -------------------------
class Restaurant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='restaurant')
    
    # Restaurant Info
    restaurant_name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to='restaurant_logos/', blank=True, null=True)
    banner = models.ImageField(upload_to='restaurant_banners/', blank=True, null=True)
    description = models.TextField(blank=True)
    
    # Contact Info
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    
    PROVINCE_CHOICES = [
        ('province1', 'Koshi Province'),
        ('madhesh', 'Madhesh Province'),
        ('bagmati', 'Bagmati Province'),
        ('gandaki', 'Gandaki Province'),
        ('lumbini', 'Lumbini Province'),
        ('karnali', 'Karnali Province'),
        ('sudurpashchim', 'Sudurpashchim Province'),
    ]
    province = models.CharField(max_length=20, choices=PROVINCE_CHOICES)
    
    # Location Coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text='Latitude coordinate (e.g., 27.717245)')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text='Longitude coordinate (e.g., 85.323960)')
    
    # Food Delivery Specific
    cuisines = models.CharField(max_length=500, blank=True, help_text='e.g., Indian, Chinese, Pizza')
    min_order_value = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    avg_prep_time = models.PositiveIntegerField(default=30, help_text='Average prep time in minutes')
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0, help_text='Average rating out of 5')
    
    # KYC Documents
    pan_number = models.CharField(max_length=15, unique=True)
    pan_document = models.FileField(
        upload_to='kyc/pan/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Upload PAN certificate (PDF/Image)'
    )
    
    # Citizenship or Company Registration
    citizenship_number = models.CharField(max_length=20, blank=True, help_text='For individuals')
    citizenship_front = models.FileField(
        upload_to='kyc/citizenship/',
        blank=True,
        validators=[FileExtensionValidator(['pdf','jpg', 'jpeg', 'png'])],
        help_text='Front side of citizenship'
    )
    citizenship_back = models.FileField(
        upload_to='kyc/citizenship/',
        blank=True,
        validators=[FileExtensionValidator(['pdf','jpg', 'jpeg', 'png'])],
        help_text='Back side of citizenship'
    )
    
        # For Company Registration
    company_registration = models.FileField(
        upload_to='kyc/company/',
        blank=True,
        validators=[FileExtensionValidator(['pdf','jpg', 'jpeg', 'png'])],
        help_text='For companies: Company registration certificate'
    )
    # Bank Details for Payment
    qr_image = models.ImageField(upload_to='restaurant_qr/', blank=True, null=True)
    
    # Status & Verification
    VERIFICATION_STATUS = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved'),
    ]
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    rejection_reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    is_open = models.BooleanField(default=True)  # Real-time open/closed status
    
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Always regenerate slug from restaurant_name
        base_slug = slugify(self.restaurant_name)
        slug = base_slug
        counter = 1
        
        # Check for uniqueness, excluding the current restaurant
        while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        self.slug = slug
        
        # Automatically set user role to restaurant
        if self.user:
            user_role, created = UserRole.objects.get_or_create(user=self.user)
            user_role.role = 'restaurant'
            user_role.save()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.restaurant_name
    
    def get_average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(r.rating for r in reviews) / len(reviews)
        return 0
        
class AdBanner(models.Model):
    """
    Advertisement Banner Model for displaying ads
    """
    # Basic Info
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Image
    image = models.ImageField(upload_to='ad_banners/', help_text='Banner image')
    
    # Links & CTA
    link_url = models.URLField(max_length=500, blank=True, null=True, help_text='Where the banner should link to')
    cta_text = models.CharField(max_length=50, default='Learn More', help_text='Call to Action button text')
    
    # Targeting (Optional)
    restaurant = models.ForeignKey(
        'Restaurant', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='ad_banners',
        help_text='Specific restaurant for this ad (leave blank for global ads)'
    )
    
    # Scheduling
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True, help_text='Leave blank for never expire')
    
    # Display settings
    order = models.PositiveIntegerField(default=0, help_text='Display order')
    is_active = models.BooleanField(default=True)
    clicks = models.PositiveIntegerField(default=0, help_text='Number of clicks')
    impressions = models.PositiveIntegerField(default=0, help_text='Number of views')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Ad Banner'
        verbose_name_plural = 'Ad Banners'
    
    def __str__(self):
        return f"{self.title or 'Ad Banner'}"
    
    def is_valid(self):
        """Check if ad is currently active and within date range"""
        if not self.is_active:
            return False
        
        now = timezone.now()
        
        # Check if banner has started
        if now < self.start_date:
            return False
        
        # Check if banner has expired (only if end_date exists)
        if self.end_date and now > self.end_date:
            return False
        
        return True
    
    def increment_clicks(self):
        """Increment click counter"""
        self.clicks += 1
        self.save(update_fields=['clicks'])
    
    def increment_impressions(self):
        """Increment impression counter"""
        self.impressions += 1
        self.save(update_fields=['impressions'])


class RestaurantCommission(models.Model):
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.15'),  # Default 15% commission for food delivery
        help_text='Commission rate as a decimal (e.g. 0.15 for 15%)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        percent = float(self.rate) * 100
        return f"{percent:.0f}%"

# Backward compatibility alias
VendorCommission = RestaurantCommission
    
    
class RestaurantPayoutRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]

    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE, related_name='payout_requests' , null=True, blank=True)
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_response = models.TextField(blank=True, help_text="Admin notes or reason for approval/rejection")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.restaurant.restaurant_name} - {self.requested_amount} ({self.get_status_display()})"

# Backward compatibility alias
VendorPayoutRequest = RestaurantPayoutRequest

 
            
            
# -------------------------
#  Wallet Management
# -------------------------
class RestaurantWallet(models.Model):
    restaurant = models.OneToOneField('Restaurant', on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.restaurant.restaurant_name} - Wallet Balance: {self.balance}"

    def credit(self, amount):
        """Add amount to wallet"""
        self.balance += Decimal(amount)
        self.save()

    def debit(self, amount):
        """Subtract amount from wallet if sufficient balance"""
        if self.balance >= Decimal(amount):
            self.balance -= Decimal(amount)
            self.save()
            return True
        return False

# Backward compatibility alias
VendorWallet = RestaurantWallet

# -------------------------
# Cuisine Type (Simplified Category for Food)
# -------------------------
class CuisineType(models.Model):
    """Cuisine categories for restaurants (Indian, Chinese, Pizza, etc)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='cuisines/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0, help_text='Display order')
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = 'Cuisine Types'
        ordering = ['order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while CuisineType.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name



# -------------------------
# Menu Section
# -------------------------
class MenuSection(models.Model):
    """Menu sections within a restaurant (e.g., Appetizers, Main Courses, Desserts)"""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_sections' , null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='menu_sections/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0, help_text='Display order')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ('restaurant', 'name')
    
    def __str__(self):
        return f"{self.restaurant.restaurant_name} - {self.name}"

    

# -------------------------
# Menu Item (Food Delivery)
# -------------------------
class MenuItem(models.Model):
    """Food items/dishes on restaurant menu"""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items' , null=True, blank=True )
    
    # Basic Info
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    section = models.ForeignKey(MenuSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='menu_items')
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text='For restaurant tracking')
    
    # Food Specific
    is_vegetarian = models.BooleanField(default=False)
    # is_spicy = models.BooleanField(default=False)  
    # spicy_level = models.PositiveSmallIntegerField(default=0, choices=[(i, i) for i in range(0, 6)], help_text='0=Not spicy, 5=Very spicy') 
    prep_time = models.PositiveIntegerField(default=15, help_text='Preparation time in minutes')
    
    # Dietary tags
    dietary_tags = models.ManyToManyField('FoodTag', blank=True, related_name='menu_items', help_text='Select dietary tags')
    
    # Image
    image = models.ImageField(upload_to='menu_items/')
    
    is_favorite = models.BooleanField(default=False, help_text='Mark as favorite for special promotion')
    
    # Availability
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while MenuItem.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(r.rating for r in reviews) / len(reviews)
        return 0
    
    def __str__(self):
        return f"{self.name} - {self.restaurant.restaurant_name}"

# Backward compatibility
Product = MenuItem


class MenuItemImage(models.Model):
    """Gallery images for menu items"""
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='menu_items/gallery/')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Image for {self.menu_item.name}"

# Backward compatibility
ProductImage = MenuItemImage


class MenuItemOption(models.Model):
    """Portions, sizes, and add-ons for menu items (e.g., Small/Medium/Large, Extra Cheese)"""
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='options')
    
    OPTION_TYPES = [
        ('portion', 'Portion Size'),
        ('addon', 'Add-on'),
        ('extra', 'Extra'),
    ]
    option_type = models.CharField(max_length=20, choices=OPTION_TYPES)
    name = models.CharField(max_length=100, help_text='e.g., Small, Medium, Large, Extra Cheese')
    
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('menu_item', 'option_type', 'name')
    
    def __str__(self):
        return f"{self.menu_item.name} - {self.name} (+{self.price_adjustment})"

# Backward compatibility
ProductVariant = MenuItemOption


# -------------------------
# Cart & Wishlist
# -------------------------

from django.core.exceptions import ValidationError

class Cart(models.Model):
    """
    Shopping cart supporting:
    - Authenticated users
    - Guest users (Flutter mobile app)
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart_items'
    )

    guest_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID generated by mobile app for guest users"
    )

    menu_item = models.ForeignKey(
        'MenuItem',
        on_delete=models.CASCADE,
        related_name='cart_items'
    )

    options = models.ManyToManyField(
        'MenuItemOption',
        blank=True
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    special_instructions = models.TextField(
        blank=True,
        help_text='e.g. No onions, Extra cheese'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-created_at']

        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['guest_id']),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'menu_item'],
                condition=models.Q(user__isnull=False),
                name='unique_user_cart_item'
            ),

            models.UniqueConstraint(
                fields=['guest_id', 'menu_item'],
                condition=models.Q(
                    guest_id__isnull=False,
                    user__isnull=True
                ),
                name='unique_guest_cart_item'
            ),
        ]

    def clean(self):
        """
        Cart item must belong either to:
        - authenticated user
        OR
        - guest user
        """

        if not self.user and not self.guest_id:
            raise ValidationError(
                "Either user or guest_id is required."
            )

        if self.user and self.guest_id:
            self.guest_id = None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def unit_price(self):
        """
        Single item price including options
        """
        price = self.menu_item.price

        for option in self.options.all():
            price += option.price_adjustment

        return price

    @property
    def total_price(self):
        """
        Total line price
        """
        return self.unit_price * self.quantity

    def get_total_price(self):
        return self.total_price

    def __str__(self):
        customer = (
            self.user.username
            if self.user
            else f"Guest ({self.guest_id[:8]})"
        )

        return f"{customer} - {self.quantity}x {self.menu_item.name}"

    # ---------------------------------
    # Helper Methods
    # ---------------------------------

    @classmethod
    def get_cart_for_user(
        cls,
        user=None,
        guest_id=None
    ):
        if user and user.is_authenticated:
            return cls.objects.filter(user=user)

        if guest_id:
            return cls.objects.filter(
                guest_id=guest_id,
                user__isnull=True
            )

        return cls.objects.none()

    @classmethod
    def get_cart_count(
        cls,
        user=None,
        guest_id=None
    ):
        return cls.get_cart_for_user(
            user=user,
            guest_id=guest_id
        ).count()

    @classmethod
    def clear_cart(
        cls,
        user=None,
        guest_id=None
    ):
        return cls.get_cart_for_user(
            user=user,
            guest_id=guest_id
        ).delete()

    @classmethod
    def merge_guest_cart(
        cls,
        user,
        guest_id
    ):
        """
        Move guest cart to authenticated user
        after login/signup.
        """

        guest_items = cls.objects.filter(
            guest_id=guest_id,
            user__isnull=True
        )

        for guest_item in guest_items:

            user_item, created = cls.objects.get_or_create(
                user=user,
                menu_item=guest_item.menu_item,
                defaults={
                    'quantity': guest_item.quantity,
                    'special_instructions':
                        guest_item.special_instructions
                }
            )

            if not created:
                user_item.quantity += guest_item.quantity

                if guest_item.special_instructions:
                    user_item.special_instructions = (
                        guest_item.special_instructions
                    )

                user_item.save()

            user_item.options.add(
                *guest_item.options.all()
            )

            guest_item.delete()

        return cls.objects.filter(user=user)

    @classmethod
    def clear_guest_cart(
        cls,
        guest_id
    ):
        return cls.objects.filter(
            guest_id=guest_id,
            user__isnull=True
        ).delete()

# -------------------------   
# Customer Address
# -------------------------
class Address(models.Model):
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('office', 'Office'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    
    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPES,
        default='home'
    )

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)

    address = models.TextField()
    landmark = models.CharField(
        max_length=255, 
        blank=True,
        null=True,
    )

    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)

    postal_code = models.CharField(
        max_length=20, 
        blank=True, 
        null=True
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        constraints = [
        models.UniqueConstraint(
            fields=['user', 'address_type'],
            name='unique_user_address_type'
        )
    ]

    def __str__(self):
        return f"{self.full_name} - {self.address_type}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(
                pk=self.pk
            ).update(is_default=False)

        super().save(*args, **kwargs)

# -------------------------
# Order Management
# -------------------------
class Order(models.Model):

    PROVINCE_CHOICES = [
        ("Koshi Province", "Koshi Province"),
        ("Madhesh Province", "Madhesh Province"),
        ("Bagmati Province", "Bagmati Province"),
        ("Gandaki Province", "Gandaki Province"),
        ("Lumbini Province", "Lumbini Province"),
        ("Karnali Province", "Karnali Province"),
        ("Sudurpashchim Province", "Sudurpashchim Province"),
    ]

    STATUS_CHOICES = [
        ('received', 'Order Received'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('picked_up', 'Picked Up'),
        ('assigned', 'Assigned'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('esewa', 'eSewa'),
        ('khalti', 'Khalti'),
        ('imepay', 'IME Pay'),
        ('connectips', 'ConnectIPS'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    # -------------------------
    # Order Info
    # -------------------------
    order_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        db_index=True
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    guest_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID from Flutter for guest users"
    )

    guest_ip = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    # -------------------------
    # Selected Saved Address
    # -------------------------
    address_obj = models.ForeignKey(
        'Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )

    # -------------------------
    # Shipping Info
    # -------------------------
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    address = models.TextField()
    landmark = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    province = models.CharField(
        max_length=50,
        choices=PROVINCE_CHOICES,
        null=True,
        blank=True
    )
    postal_code = models.CharField(max_length=10, blank=True)

    # -------------------------
    # Delivery Coordinates (Latitude & Longitude)
    # -------------------------
    delivery_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="Delivery location latitude (e.g., 27.7172453)"
    )

    delivery_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="Delivery location longitude (e.g., 85.3239605)"
    )

    delivery_distance_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=0,
        help_text="Calculated delivery distance in kilometers"
    )

    # -------------------------
    # Pricing
    # -------------------------
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Free for ≤5km, NPR 100 for >5km"
    )
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=13.00,
        help_text="Nepal VAT 13%"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Will be calculated dynamically based on tax percentage"
    )

    total = models.DecimalField(max_digits=10, decimal_places=2)

    # -------------------------
    # Payment
    # -------------------------
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="cod"
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid'
    )

    transaction_id = models.CharField(max_length=100, blank=True)

    coupon = models.ForeignKey(
        'Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # -------------------------
    # Status
    # -------------------------
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='received' 
    )

    # -------------------------
    # Timestamps
    # -------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    estimated_delivery_date = models.DateField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['guest_id']),
            models.Index(fields=['payment_status', 'status']),
            models.Index(fields=['delivery_latitude', 'delivery_longitude']),
        ]

    # -------------------------
    # HELPERS
    # -------------------------
    @property
    def is_guest_order(self):
        return self.user is None and self.guest_id is not None

    @property
    def customer_display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        return self.full_name or f"Guest {self.guest_id[:8] if self.guest_id else ''}"

    def can_cancel(self):
        return self.status in ['received', 'preparing'] and self.payment_status != 'paid'

    def can_request_refund(self):
        return self.status == 'delivered' and self.payment_status == 'paid'

    # -------------------------
    # Tax Methods
    # -------------------------

    def get_current_tax_rate(self):
        """ Get the current active tax rate from TaxRate table
            Returns Decimal tax percentage or None if no active tax rate found
        """
        try:
            # Get the currently active tax rate
            active_tax = TaxRate.objects.filter(is_active=True).first()
            if active_tax:
                return active_tax.tax
        except Exception as e:
            print(f"Error fetching tax rate: {e}")

        # Fallback to the stored tax_percentage if no active tax rate found
        return self.tax_percentage if self.tax_percentage else Decimal('0.00')

    def calculate_tax(self, tax_percentage=None):
        """
        Calculate tax amount dynamically using TaxRate table

        Args: 
            tax_percentage (Decimal, optional): Override tax percentage
        Returns:
            Decimal: Calculated tax amount
        """
        if tax_percentage is None:
            tax_percentage = self.get_current_tax_rate()
        
        taxable_amount = (self.subtotal or Decimal('0.00')) - (self.discount or Decimal('0.00'))
        taxable_amount = max(taxable_amount, Decimal('0.00'))
        self.tax_amount = (taxable_amount * tax_percentage / 100).quantize(Decimal('0.01'))
        self.tax_percentage = tax_percentage # store the applied tax percentage
        return self.tax_amount

    # -------------------------
    # Shipping Methods
    # -------------------------
    def calculate_shipping_cost(self, distance_km=None):
        """
        Calculate shipping cost based on delivery distance
        Rule: Free for ≤ 5 KM, NPR 100 for > 5 KM
        
        Args:
            distance_km (float, optional): Delivery distance in kilometers
        
        Returns:
            Decimal: Calculated shipping cost
        """
        if distance_km is not None:
            self.delivery_distance_km = Decimal(str(distance_km))
        
        # Check if distance is available
        if self.delivery_distance_km:
            if self.delivery_distance_km <= 5:
                self.shipping_cost = Decimal('0.00')
            else:
                self.shipping_cost = Decimal('100.00')
        else:
            self.shipping_cost = Decimal('0.00')
        
        return self.shipping_cost

    def calculate_shipping_from_coordinates(self, restaurant_lat, restaurant_lng):
        """
        Calculate shipping cost by calculating distance from restaurant coordinates
        
        Args:
            restaurant_lat (float): Restaurant latitude
            restaurant_lng (float): Restaurant longitude
        
        Returns:
            Decimal: Calculated shipping cost
        """
        distance = self.calculate_distance_to_restaurant(restaurant_lat, restaurant_lng)
        return self.calculate_shipping_cost(distance)

    # -------------------------
    # Total Calculation Methods
    # -------------------------
    def calculate_total(self):
        """Calculate total amount (subtotal + shipping + tax - discount)"""
        self.total = (self.subtotal + self.shipping_cost + self.tax_amount - self.discount).quantize(Decimal('0.01'))
        return self.total

    def calculate_grand_total(self, tax_percentage=None, distance_km=None, recalc_tax=True, recalc_shipping=True):
        """
        Calculate grand total with all components
        
        Args:
            tax_percentage (Decimal, optional): Override tax percentage
            distance_km (float, optional): Delivery distance in kilometers
            recalc_tax (bool): Whether to recalculate tax
            recalc_shipping (bool): Whether to recalculate shipping
        
        Returns:
            Decimal: Grand total
        """
        # Recalculate tax if requested
        if recalc_tax:
            self.calculate_tax(tax_percentage)
        
        # Recalculate shipping if requested
        if recalc_shipping:
            self.calculate_shipping_cost(distance_km)
        
        # Calculate total
        self.total = (self.subtotal + self.shipping_cost + self.tax_amount - self.discount).quantize(Decimal('0.01'))
        
        return self.total

    # -------------------------
    # Delivery Location Methods
    # -------------------------
    def has_valid_delivery_location(self):
        """Check if delivery location coordinates are provided"""
        return self.delivery_latitude is not None and self.delivery_longitude is not None

    def get_delivery_coordinates(self):
        """Return delivery coordinates as tuple"""
        if self.has_valid_delivery_location():
            return (float(self.delivery_latitude), float(self.delivery_longitude))
        return None

    def calculate_distance_to_restaurant(self, restaurant_lat, restaurant_lng):
        """
        Calculate distance from restaurant to delivery location using Haversine formula
        
        Args:
            restaurant_lat (float): Restaurant latitude
            restaurant_lng (float): Restaurant longitude
        
        Returns:
            float: Distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2
        
        if not self.has_valid_delivery_location():
            return 0
        
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1 = radians(restaurant_lat), radians(restaurant_lng)
        lat2, lon2 = radians(float(self.delivery_latitude)), radians(float(self.delivery_longitude))
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance_km = R * c
        
        return round(distance_km, 2)

    def update_delivery_charges(self, restaurant_lat, restaurant_lng):
        """
        Update shipping cost based on distance from restaurant
        
        Args:
            restaurant_lat (float): Restaurant latitude
            restaurant_lng (float): Restaurant longitude
        
        Returns:
            float: Calculated distance in kilometers
        """
        distance = self.calculate_distance_to_restaurant(restaurant_lat, restaurant_lng)
        self.delivery_distance_km = Decimal(str(distance))
        self.calculate_shipping_cost(distance)
        self.calculate_total()
        self.save()
        
        return distance
    
    # -------------------------
    # SAVE METHOD
    # -------------------------
    def save(self, *args, **kwargs):

        if not self.order_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = uuid.uuid4().hex[:6].upper()
            self.order_number = f"ORD{timestamp}{unique_id}"

        # Always ensure calculations are correct
        self.calculate_tax()
        self.calculate_total()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} - {self.customer_display_name}"


class OrderItem(models.Model):
    """Individual items within an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('MenuItem', on_delete=models.SET_NULL, null=True, related_name='order_items')
    options = models.ManyToManyField(MenuItemOption, blank=True)  # Sizes, add-ons
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    special_instructions = models.TextField(blank=True, help_text='Special cooking preferences')

    def get_item_price(self):
        """Price for a single unit including options"""
        total_price = self.price 
        for option in self.options.all():
            total_price += option.price_adjustment
        return total_price

    def get_total(self):
        """Total price for this line item"""
        return self.get_item_price() * self.quantity

    def __str__(self):
        item_name = self.menu_item.name if self.menu_item else "Deleted Item"

        option_names = ", ".join(o.name for o in self.options.all())

        if option_names:
            return f"{self.quantity} x {item_name} ({option_names})"

        return f"{self.quantity} x {item_name}"

# Backward compatibility
Product = MenuItem


# -------------------------
# Restaurant Reviews & Ratings
# -------------------------
class RestaurantReview(models.Model):
    """Ratings and reviews for restaurants"""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews' , null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    
    # Rating breakdown
    food_quality_rating = models.PositiveSmallIntegerField(default=0, choices=[(i, str(i)) for i in range(1, 6)], blank=True)
    delivery_rating = models.PositiveSmallIntegerField(default=0, choices=[(i, str(i)) for i in range(1, 6)], blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('restaurant', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.restaurant.restaurant_name} ({self.rating}★)"

# Backward compatibility
Review = RestaurantReview


class MenuItemReview(models.Model):
    """Ratings for individual menu items"""
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('menu_item', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.menu_item.name} ({self.rating}★)"


# -------------------------
# Delivery Zone Management
# -------------------------
class DeliveryZone(models.Model):
    """Define delivery service areas for restaurants"""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='delivery_zones' , null=True, blank=True)
    name = models.CharField(max_length=100, help_text='e.g., Zone A, North Kathmandu')
    
    # Location coordinates (for geo-fencing)
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_km = models.FloatField(default=5, help_text='Delivery radius in kilometers')
    
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    delivery_time_min = models.PositiveIntegerField(default=30, help_text='Min delivery time in minutes')
    delivery_time_max = models.PositiveIntegerField(default=60, help_text='Max delivery time in minutes')
    
    min_order_value = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Minimum order for this zone')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.restaurant.restaurant_name} - {self.name}"


# -------------------------
# Restaurant Operating Hours
# -------------------------
class RestaurantTiming(models.Model):
    """Restaurant opening hours and holidays"""
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE, related_name='timing')
    
    # Standard hours
    monday_open = models.TimeField(default='10:00')
    monday_close = models.TimeField(default='22:00')
    tuesday_open = models.TimeField(default='10:00')
    tuesday_close = models.TimeField(default='22:00')
    wednesday_open = models.TimeField(default='10:00')
    wednesday_close = models.TimeField(default='22:00')
    thursday_open = models.TimeField(default='10:00')
    thursday_close = models.TimeField(default='22:00')
    friday_open = models.TimeField(default='10:00')
    friday_close = models.TimeField(default='23:00')
    saturday_open = models.TimeField(default='09:00')
    saturday_close = models.TimeField(default='23:00')
    sunday_open = models.TimeField(default='09:00')
    sunday_close = models.TimeField(default='22:00')
    
    is_open = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.restaurant.restaurant_name} - Operating Hours"


class RestaurantHoliday(models.Model):
    """Closed dates for restaurant"""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='holidays' , null=True, blank=True)
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)
    
    class Meta:
        unique_together = ('restaurant', 'date')
    
    def __str__(self):
        return f"{self.restaurant.restaurant_name} - Closed on {self.date}"


# -------------------------
# Food Tags
# -------------------------
class FoodTag(models.Model):
    """Food tags for filtering (Vegetarian, Vegan, Gluten-Free, etc)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=100, blank=True, help_text='Icon class or emoji')
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
# -------------------------
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    
    DISCOUNT_TYPES = [
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text='Minimum order value')
    
    # Usage limits
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text='Total usage limit')
    usage_limit_per_user = models.PositiveIntegerField(null=True, blank=True, help_text='Per user limit')
    used_count = models.PositiveIntegerField(default=0)
    
    # Validity
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    

    
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self, user=None, cart_items=None):
        """Check if coupon is valid for the user and cart"""
        now = timezone.now()
        # Basic checks: active and date
        if not (self.is_active and self.valid_from <= now <= self.valid_to):
            return False, "This coupon is not active or has expired."

        # Check total usage limit
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False, "This coupon has reached its usage limit."

        # Check per-user usage
        if user and self.usage_limit_per_user is not None:
            user_used_count = CouponUsage.objects.filter(user=user, coupon=self).count()
            if user_used_count >= self.usage_limit_per_user:
                return False, "You have already used this coupon the maximum number of times."

        # Check minimum purchase
        if cart_items is not None:
            subtotal = sum(item.get_item_price() * item.quantity for item in cart_items)
            if hasattr(self, 'min_purchase') and subtotal < self.min_purchase:
                return False, f"Minimum order amount of Rs {self.min_purchase} required."

        return True, "Coupon is valid."

    def get_discount_amount(self, subtotal):
        """Calculate discount based on subtotal"""
        if self.discount_type == 'percent':
            discount = (self.discount_value / 100) * subtotal
        else:
            discount = self.discount_value
        return discount
    
    def __str__(self):
        return self.code


class CouponUsage(models.Model):
    """Track coupon usage per user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    order = models.ForeignKey('Order', on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.first_name} used {self.coupon.code}"


# -------------------------
# Tax rate
# -------------------------
class TaxRate(models.Model):
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=13, help_text="Tax percentage (e.g. 13 for 13%)")
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tax}%"
    
    @classmethod
    def get_active_tax(cls):
        """Get the active tax rate"""
        tax_rate = cls.objects.filter(is_active=True).first()
        if tax_rate:
            return tax_rate.tax
        return Decimal('0.00')  # Return 0 if no tax rate found

# -------------------------
#  Invoice
# -------------------------
class Invoice(models.Model):
    invoice_number = models.CharField(max_length=20,null=True, unique=True, editable=False)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='invoices')
    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE, related_name='invoices', null= True, blank= True)
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Guest customer fields (for non-authenticated users)
    is_guest = models.BooleanField(default=False)
    guest_name = models.CharField(max_length=200, blank=True)
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=15, blank=True)
    
    # Billing address from order (for both registered and guest users)
    billing_full_name = models.CharField(max_length=200, blank=True)
    billing_phone = models.CharField(max_length=15, blank=True)
    billing_email = models.EmailField(blank=True)
    billing_address = models.TextField(blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_province = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Totals
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=13)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    payment_status = models.CharField(max_length=20, choices=[
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('failed', 'Failed')
    ], default='pending')
    
    notes = models.TextField(blank=True, null=True)

    def get_customer_display_name(self):
        """Return display name for customer (registered or guest)"""
        if self.is_guest:
            return self.guest_name or self.billing_full_name or "Guest Customer"
        return self.customer.get_full_name() or self.customer.username if self.customer else "Unknown"

    def get_customer_email(self):
        """Return email (registered or guest)"""
        if self.is_guest:
            return self.guest_email or self.billing_email
        return self.customer.email if self.customer else ""

    def get_customer_phone(self):
        """Return phone (registered or guest)"""
        if self.is_guest:
            return self.guest_phone or self.billing_phone
        # Try to get phone from user profile
        if self.customer and hasattr(self.customer, 'profile'):
            return self.customer.profile.phone
        return ""

    def get_default_restaurant():
        """Get the default restaurant for the system"""
        from .models import Restaurant
        return Restaurant.objects.first()

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Use a short UUID to guarantee uniqueness
            self.invoice_number = f"INV{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.order.order_number}"


# -------------------------
# Organization Info
# -------------------------
class Organization(models.Model):
    # Basic Info
    name = models.CharField(max_length=200, default="My Store")
    logo = models.ImageField(upload_to='org/', blank=True, null=True)
    
    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    phone_secondary = models.CharField(max_length=15, blank=True)
    address = models.TextField()
    
    # Social Media
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    tiktok = models.URLField(blank=True)
    
    class Meta:
        verbose_name = 'Organization Info'
        verbose_name_plural = 'Organization Info'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.pk and Organization.objects.exists():
            raise ValueError('Only one Organization instance allowed')
        super().save(*args, **kwargs)


# -------------------------
# Newsletter
# -------------------------
class Newsletter(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.email


# -------------------------
# Contact Messages
# -------------------------
class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    
    is_read = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message from {self.name}"


# -------------------------
# Notifications
# -------------------------
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    NOTIFICATION_TYPES = [
        ('order', 'Order Update'),
        ('product', 'Product Update'),
        ('message', 'Message'),
        ('promotion', 'Promotion'),
        ('other', 'Other'),
    ]
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.URLField(blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    
   

# Slider model
class Slider(models.Model):

    image = models.ImageField(upload_to='sliders/')
    is_active = models.BooleanField(default=True)
    link = models.URLField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return  f"Slider {self.id}"



class Banner(models.Model):
    PAGE_CHOICES = [
        ('home', 'Home Page'),
        ('products', 'Products Page'),
      
    ]

    title = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to='banners/')
    link = models.URLField(max_length=500, blank=True, null=True)
    page = models.CharField(
        max_length=50, 
        choices=PAGE_CHOICES, 
        default='home', 
        unique=True,  # Only one banner per page
        help_text="Select where to display the banner"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title or f"Banner {self.id}"


# ===========================
#   Signals 
# ===========================

@receiver(post_save, sender=Order)
def auto_create_invoice(sender, instance, created, **kwargs):
    """Auto-create invoice when order is placed (handles guest customers)"""
    if created:
        from .models import Restaurant
        default_restaurant = Restaurant.objects.first()
        
        # Determine if this is a guest order (no user associated or anonymous user)
        is_guest = instance.user is None
        
        # Prepare invoice data
        invoice_data = {
            'order': instance,
            'restaurant': default_restaurant,
            'subtotal': instance.subtotal,
            'tax_percentage': instance.tax_percentage,
            'tax_amount': instance.tax_amount,
            'discount': instance.discount,
            'total': instance.total,
            'shipping_cost': instance.shipping_cost,
            'payment_status': 'pending' if instance.payment_status == 'unpaid' else 'paid',
            'notes': f"Invoice for order {instance.order_number}",
            
            # Always copy billing/shipping details from order
            'billing_full_name': instance.full_name,
            'billing_phone': instance.phone,
            'billing_email': instance.email,
            'billing_address': instance.address,
            'billing_city': instance.city,
            'billing_province': instance.province,
        }
        
        # Handle guest vs registered user
        if is_guest:
            invoice_data['is_guest'] = True
            invoice_data['guest_name'] = instance.full_name
            invoice_data['guest_email'] = instance.email
            invoice_data['guest_phone'] = instance.phone
            invoice_data['customer'] = None  # No user association
        else:
            invoice_data['is_guest'] = False
            invoice_data['customer'] = instance.user
            # For registered users, also store their details from order
            # (in case they change their profile later)
            invoice_data['guest_name'] = ''  # Clear guest fields
            invoice_data['guest_email'] = ''
            invoice_data['guest_phone'] = ''
        
        Invoice.objects.create(**invoice_data)
        print(f"Invoice created for {instance.order_number} (Guest: {is_guest})")


@receiver(post_save, sender=Order)
def credit_restaurant_wallet_on_order_complete(sender, instance, **kwargs):
    """
    Credit restaurant wallet when an order is delivered.
    Deducts platform commission using RestaurantCommission.
    """
    if instance.status == 'delivered':
        for item in instance.items.all():
            restaurant = item.menu_item.restaurant
            if restaurant:
                # Get restaurant-specific commission or fallback to default 15%
                rc = RestaurantCommission.objects.first()
                rate = rc.rate if rc else Decimal('0.15')

                total_amount = Decimal(item.get_total())
                platform_commission = (total_amount * rate).quantize(Decimal('0.01'))
                restaurant_earning = (total_amount - platform_commission).quantize(Decimal('0.01'))

                wallet, _ = RestaurantWallet.objects.get_or_create(restaurant=restaurant)
                wallet.credit(restaurant_earning)


@receiver(post_save, sender=RestaurantPayoutRequest)
def process_restaurant_payout_request(sender, instance, **kwargs):
    """
    Process restaurant payout request by debiting wallet if approved.
    """
    if instance.status == 'paid':
        wallet, _ = RestaurantWallet.objects.get_or_create(restaurant=instance.restaurant)
        wallet.debit(instance.requested_amount)




@receiver(post_save, sender=Order)
def change_invoice_payment_status_with_order(sender, instance, **kwargs):
    """
    Sync payment status of invoices with the order's payment status.
    Only updates existing invoices, does NOT create new ones.
    """
    # Get all invoices for this order
    invoices = Invoice.objects.filter(order=instance)

    for invoice in invoices:
        # Update invoice payment status based on order
        if instance.payment_status == "unpaid":
            invoice.payment_status = "pending"
        elif instance.payment_status == "paid":
            invoice.payment_status = "paid"
        elif instance.payment_status == "failed":
            invoice.payment_status = "failed"
        else:
            invoice.payment_status = "pending"

        invoice.save()  # Save the updated invoice



@receiver(post_save, sender=User)
def create_user_role_and_profile(sender, instance, created, **kwargs):
    """
    Automatically creates a UserRole and UserProfile
    when a new user (including superuser) is created.
    """

    # Run only when a new user is created
    if created and instance.is_superuser:
        UserRole.objects.get_or_create(role="admin",user=instance)
        UserProfile.objects.get_or_create(user=instance)
        print("created")


@receiver(post_save, sender = DeliveryAssignment )
def sync_order_status_with_delivery(sender, instance, created, **kwargs):
    print(f"Signal fired for DeliveryAssignment {instance.id} with status {instance.status}")


    order = instance.order
    if instance.status == 'picked_up' and order.status != 'picked_up':
        order.status= 'picked_up'
        order.save()
    elif instance.status == 'in_transit' and order.status != 'in_transit':
        order.status= 'in_transit'
        order.save()
    elif instance.status == 'delivered' and order.status != 'delivered':
        order.status= 'delivered'
        order.delivered_at = timezone.now()
        order.save()
    elif instance.status == 'failed':
        order.status= 'cancelled'
        order.save()



