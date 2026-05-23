from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Add 'role' to the fieldsets shown in admin
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Profile', {'fields': ('role',)}),
    )
    list_display = ['username', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    raw_id_fields = ['user']  # search widget instead of dropdown (better for large datasets)