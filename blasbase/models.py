from django.db import models
from django.db.models import F, Q

import datetime
from blasbase import validators
from django.utils.translation import ugettext_lazy as _
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.db.models.query import QuerySet

from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    Permission,
    PermissionsMixin
)

from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill

from django_countries.fields import CountryField

from mptt.models import TreeManager, MPTTModel, TreeForeignKey

from blapi.settings import DEFAULT_FROM_EMAIL


class Address(models.Model):
    address = models.CharField(max_length=256, blank=True, verbose_name=_('address'))
    post_code = models.CharField(max_length=256, blank=True, verbose_name=_('post code'))  # Byt namn till post_code
    city = models.CharField(max_length=256, blank=True, verbose_name=_('city'))
    country = CountryField()
    person = models.ForeignKey('blasbase.Person', related_name='addresses')


class PhoneNumber(models.Model):
    number = models.CharField(max_length=64)
    country = CountryField()
    person = models.ForeignKey('blasbase.Person', related_name='phone_numbers')


class PersonQuerySet(models.QuerySet):
    def members(self):
        return self.filter(assignments__in=Assignment.objects.memberships()).distinct()

    def active(self):
        """Hämtar personer som är relaterade till aktiva assignments. distinct() tar bort eventuella dubletter."""
        return self.filter(assignments__in=Assignment.objects.active()).distinct()

    def oldies(self):
        """Hämtar personer som är relaterade till utgångna assignments (för att hitta personerna som _varit_ medlemmar)
        och exkluderar sedan personer som har relationer till aktiva dito. distinct() tar bort eventuella dubletter."""
        return self.filter(assignments__in=Assignment.objects.oldies()).exclude(
            assignments__in=Assignment.objects.active()).distinct()

    def others(self):
        return self.exclude(assignments__in=Assignment.objects.memberships()).distinct()


class Person(models.Model):
    """
    Stores information about a real life person.
    This is not a user of the website. However, a
    user may be associated with a Person.
    """

    first_name = models.CharField(max_length=256, verbose_name=_('first name'))
    nickname = models.CharField(max_length=256, blank=True, verbose_name=_('nickname'))
    last_name = models.CharField(max_length=256, verbose_name=_('last name'))

    born = models.DateField(blank=True, null=True, verbose_name=_('born'),
                            validators=[validators.date_before_today])
    deceased = models.DateField(blank=True, null=True, verbose_name=_('deceased'),
                                validators=[validators.date_before_today])

    personal_id_num_suffix = models.CharField(max_length=4, blank=True,
                                              verbose_name=_('last 4 charactes of personal identification number'))

    liu_id = models.CharField(max_length=8, blank=True, verbose_name=_('LiU-ID'))

    about = models.TextField(blank=True, verbose_name=_('about'))

    special_diets = models.ManyToManyField('SpecialDiet', related_name='people', blank=True,
                                           verbose_name=_('special diets'))
    special_diets_extra = models.CharField(max_length=256, blank=True, verbose_name=_('special diets comments'))

    avatar = ProcessedImageField(null=True, blank=True,
                                 upload_to='avatars',
                                 processors=[ResizeToFill(400, 600)],
                                 format='JPEG',
                                 options={'quality': 90})
    email = models.EmailField(max_length=256, null=True, blank=True)

    last_updated = models.DateTimeField(auto_now=True, verbose_name=_('last updated'))

    functions = models.ManyToManyField('Function', through='Assignment', verbose_name=_('functions'))

    user = models.OneToOneField('BlasUser', null=True, blank=True, related_name='person')

    objects = PersonQuerySet.as_manager()

    def __str__(self):
        return self.get_full_name()

    def clean(self):
        cleaned_data = super(Person, self).clean()

        # Validera endast om både födelse- och dödsdatum angetts.
        if self.born and self.deceased:
            validators.datetime_before_datetime(self.born, self.deceased, _('Decease date must be after birth date.'))
        return cleaned_data

    # Används internt av Django
    def get_full_name(self):
        if self.nickname:
            return u'{0} "{1}" {2}'.format(self.first_name, self.nickname, self.last_name)  # Leif "Pappa Blås" Holm

        return u'{0} {1}'.format(self.first_name, self.last_name)  # Leif Holm

    # Används internt av Django
    def get_short_name(self):
        if self.nickname:
            return self.nickname  # Pappa Blås

        return u'{0} {1}'.format(self.first_name, self.last_name[0])  # Leif H

    full_name = property(get_full_name)
    short_name = property(get_short_name)


class FunctionManagerMixin(TreeManager):
    def descendants(self, include_self=False):
        return self.get_queryset_descendants(self, include_self=include_self).distinct()

    def ancestors(self, include_self=False):
        return self.get_queryset_ancestors(self, include_self=include_self).distinct()

    def people(self):
        """
        Returns people from self and all descendants. Does not and should not care about start/end dates.
        """
        return Person.objects.filter(functions__in=self.all())

    def permissions(self):
        """
        Returns permissions from self and all ancestors.
        """
        return Permission.objects.filter(functions__in=self.all())



class FunctionQuerySet(QuerySet, FunctionManagerMixin):
    pass


class FunctionManager(FunctionManagerMixin):
    def get_queryset(self):
        return FunctionQuerySet(model=self.model, using=self._db).order_by(self.tree_id_attr, self.left_attr)


class Function(MPTTModel):
    name = models.CharField(max_length=256, verbose_name=_('name'))
    description = models.TextField(blank=True, verbose_name=_('description'))
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', verbose_name=_('parent'))

    permissions = models.ManyToManyField(Permission, related_name='functions', blank=True, verbose_name=_('permissions'))

    membership = models.BooleanField(default=False, verbose_name=_('membership'))
    engagement = models.BooleanField(default=False, verbose_name=_('engagement'))

    objects = FunctionManager()

    class Meta:
        unique_together = ('parent', 'name')

    class MPTTMeta:
        order_insertion_by = ('name',)

    def __str__(self):
        return u'{0}'.format(self.name)

    def get_people(self):
        return self.get_descendants(include_self=True).people()

    def get_inherited_permissions(self):
        return self.get_ancestors(include_self=True).permissions()



class SpecialDiet(models.Model):
    name = models.CharField(max_length=256, verbose_name=_('name'))

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class AssignmentQuerySet(models.QuerySet):
    def sane(self):
        """
        Returns sane assignments, i.e. all except those with an earlier end date than start date.

        This isn't really used in production, but could be useful to find invalid assignment if it would happen.
        """
        return self.filter(Q(end__gte=F('start')) | Q(start__isnull=True) | Q(end__isnull=True))

    def defined(self):
        """
        Returns assignments with at least start or end date.
        """
        return self.exclude(start__isnull=True, end__isnull=True)

    def ongoing(self, date=datetime.date.today()):
        """
        Returns *defined* assignments with...

        Start date undefined or before date
        AND
        End date undefined or after date

        :param date: datetime.date object, default today
        """
        return self.defined().filter(
            Q(start__isnull=True) | Q(start__lte=date),
            Q(end__isnull=True) | Q(end__gte=date)
        )

    def ended(self, date=datetime.date.today()):
        return self.filter(
            Q(end__lt=date) | Q(start__isnull=True, end__isnull=True)
        )

    def memberships(self, all=False):
        qs = self.filter(function__membership=True).order_by('start')
        if not all:
            qs = qs.exclude(trial=True)
        return qs

    def engagements(self, all=False):
        qs = self.filter(function__engagement=True).order_by('start')
        if not all:
            qs = qs.exclude(trial=True)
        return qs

    def active(self):
        return self.memberships().ongoing()

    def oldies(self):
        return self.memberships().ended()


class Assignment(models.Model):
    """Mellantabell som innehåller info om varje användares medlemsskap/uppdrag på olika poster."""
    person = models.ForeignKey(Person, related_name='assignments', verbose_name=_('person'))
    function = TreeForeignKey(Function, verbose_name=_('function'))

    start = models.DateField(blank=True, null=True, verbose_name=_('start'), help_text=_('First date of assignment.'))
    end = models.DateField(blank=True, null=True, verbose_name=_('end'), help_text=_('Last date of assignment.'))

    trial = models.BooleanField(default=False, verbose_name=_('trial'))

    objects = AssignmentQuerySet.as_manager()

    class Meta:
        ordering = ['start']

    def __str__(self):
        return u'{0}: {1}'.format(self.person.get_short_name(), self.function)

    @property
    def membership(self):
        return self.function.membership

    @property
    def engagement(self):
        return self.function.engagement

    @property
    def sane(self):
        return not self.start or not self.end or not self.start > self.end

    @property
    def defined(self):
        """
        Returns False if neither start nor end are set. Otherwise True.
        """
        return self.start or self.end

    @property
    def ongoing(self, date=datetime.date.today()):
        if not self.defined or not self.sane:
            return False
        elif (not self.start or self.start <= date) and (not self.end or self.end >= date):
            return True
        else:
            return False


class UserManager(BaseUserManager):

    def create_user(self, email, password):
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(email=self.normalize_email(email))

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        user = self.create_user(email=email, password=password)
        user.is_staff = True
        user.is_superuser = True

        user.save(using=self._db)
        return user


class BlasUser(AbstractBaseUser, PermissionsMixin):

    email = models.EmailField(unique=True, db_index=True)

    is_active = models.BooleanField(default=True, verbose_name=_('is active'),
                                    help_text=u"Används för att avgöra ifall användaren kan logga in eller inte. Detta är INTE ett fält för att markera att någon blivit gamling")
    is_staff = models.BooleanField(default=False, verbose_name=_('is staff'),
                                   help_text=u'Bestämmer om användaren kan logga in i admingränssnittet')

    extra_name = models.CharField(max_length=64, default="")

    objects = UserManager()

    USERNAME_FIELD = 'email'

    class Meta:
        ordering = ['email']

    def __str__(self):
        return self.get_full_name()

    def get_assignment_permissions(self, obj=None):
        if not hasattr(self, 'person'):
            return set()

        """Hämtar rättigheter från den kopplade personens poster och sektioner"""
        perms = set()
        # set(["%s.%s" % (p.content_type.app_label, p.codename) for p in user_obj.user_permissions.select_related()])
        for assignment in self.person.assignments.ongoing():
            perms.update(assignment.function.get_inherited_permissions())
        return perms

    def get_full_name(self):
        if hasattr(self, 'person'):
            return self.person.full_name
        elif self.extra_name is not None and self.extra_name != "":
            return self.extra_name
        else:
            return self.email

    def get_short_name(self):
        if hasattr(self, 'person'):
            return self.person.short_name
        elif self.extra_name is not None:
            return self.extra_name
        else:
            return self.email

    @property
    def short_name(self):
        return self.get_short_name()
