from django.contrib import admin
from django.contrib.auth import password_validation
from django.contrib.auth.admin import UserAdmin
from .forms import BlasUserCreationForm, BlasUserChangeForm

from django.utils.translation import ugettext_lazy as _
from .models import BlasUser


@admin.register(BlasUser)
class BlasUserAdmin(UserAdmin):

    max_num = 1
    extra = 0

    list_display = ('email', 'is_staff')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Rättigheter'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (None, {'fields': ('last_login',)})
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide', ),
            'fields': ('email', 'password')
        }),
    )

    add_form = BlasUserCreationForm
    ordering = ('email',)