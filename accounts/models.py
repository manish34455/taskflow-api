from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager — must extend BaseUserManager, not models.Manager"""

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(username, email, password, **extra_fields)

    def admins(self):
        return self.get_queryset().filter(role=User.ADMIN)

    def managers(self):
        return self.get_queryset().filter(role=User.MANAGER)

    def developers(self):
        return self.get_queryset().filter(role=User.DEVELOPER)

    def active(self):
        return self.get_queryset().filter(is_active=True)


class User(AbstractUser):
    ADMIN = 'admin'
    MANAGER = 'manager'
    DEVELOPER = 'developer'

    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (MANAGER, 'Manager'),
        (DEVELOPER, 'Developer'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=DEVELOPER,
        db_index=True,
    )
    email = models.EmailField(unique=True)

    objects = UserManager()

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_admin(self):
        return self.role == self.ADMIN

    @property
    def is_manager(self):
        return self.role == self.MANAGER

    @property
    def is_developer(self):
        return self.role == self.DEVELOPER

    class Meta:
        db_table = 'users'


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    bio = models.TextField(blank=True, default='')
    avatar_url = models.URLField(blank=True, default='')
    github_url = models.URLField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile of {self.user.username}'

    class Meta:
        db_table = 'user_profiles'