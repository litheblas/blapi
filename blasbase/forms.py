
from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import Site
from django.contrib.auth.forms import UserChangeForm, PasswordResetForm
from django import forms
from .models import BlasUser

from django.core.mail import EmailMultiAlternatives
from django.template import loader
from blapi.settings import DEFAULT_FROM_EMAIL

from django.utils.crypto import get_random_string
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_bytes


class BlasUserCreationForm(forms.ModelForm):
    email = forms.EmailField(max_length=64)

    password = forms.CharField(
        label=_("Password"),
        strip=False,
        required=False,
        help_text=_("Lämna blankt för att skicka en engångslänk till användaren som de använder för att sätta sitt lösenord"),
    )

    class Meta:
        model = BlasUser
        fields = ("email",)

    def clean_password(self):
        password = self.cleaned_data.get("password")
        self.instance.email = self.cleaned_data.get('email')
        if password == "":
            return None
        else:
            password_validation.validate_password(self.cleaned_data.get('password'), self.instance)
            return password

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')

        email_message.send()

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.cleaned_data["password"] is None:
            """
            Set a temporary password, since reset isn't allowed on unusable passwords
            """
            user.set_password(get_random_string(20))
            user.save()

            subject_template_name = 'registration/password_reset_subject.txt'
            email_template_name = 'registration/password_reset_email.html'
            use_https = True
            token_generator = default_token_generator
            from_email = DEFAULT_FROM_EMAIL
            """
            Generate a one-use only link for resetting password and send it to the
            user.
            """
            email = self.cleaned_data["email"]
            current_site = Site.objects.get_current()
            site_name = current_site.name
            domain = current_site.domain
            context = {
                'email': email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)).decode(),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }

            self.send_mail(
                subject_template_name, email_template_name, context, from_email, email,
            )
        else:
            user.set_password(self.cleaned_data["password"])
            user.save()

        return user

    class Meta:
        model = BlasUser
        fields = ("email",)


class BlasUserChangeForm(UserChangeForm):

    def __init__(self, *args, **kargs):
        super(BlasUserChangeForm, self).__init__(*args, **kargs)
        #del self.fields['username']

    class Meta:
        model = BlasUser
        fields = '__all__'
