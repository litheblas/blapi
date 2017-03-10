from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import BlasUserCreationForm

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Group
from .models import BlasUser, Person, Assignment, Function
from mptt.admin import DraggableMPTTAdmin

@admin.register(BlasUser)
class BlasUserAdmin(UserAdmin):
    max_num = 1
    extra = 0

    readonly_fields = ('person',)

    list_display = ('email', 'is_staff', 'person')

    fieldsets = (
        (None, {'fields': ('email', 'password', 'person')}),
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


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 1
    raw_id_fields = ('function',)


@admin.register(Function)
class FunctionAdmin(DraggableMPTTAdmin):
    model = Function

    list_display = ('tree_actions', 'indented_title', 'name', 'membership', 'engagement')
    filter_horizontal = ('permissions',)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    inlines = [AssignmentInline]

    raw_id_fields = ('user',)

    fieldsets = (
        (None, {'fields': (('first_name', 'nickname', 'last_name',),
                           'avatar',
                           'email',
                           'user',
                           'born',
                           'deceased',
                           'personal_id_num_suffix',
                           'liu_id',
                           'about',
                           'special_diets',
                           'special_diets_extra'
                           )}),
    )

    list_display = ('first_name', 'nickname', 'last_name')

admin.site.unregister(Group)