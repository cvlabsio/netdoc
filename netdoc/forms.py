from email.policy import default
from django import forms

from dcim.models import Device
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm, NetBoxModelCSVForm, NetBoxModelBulkEditForm
from utilities.forms import CSVModelChoiceField, DynamicModelChoiceField, StaticSelect, BOOLEAN_WITH_BLANK_CHOICES, add_blank_choice
from utilities.forms.fields import DynamicModelChoiceField
from .models import Credential, Discoverable, DiscoveryLog, DiscoveryModeChoices, DiscoveryModeChoices
from dcim.models import Site


#
# Credential forms
#

class CredentialForm(NetBoxModelForm):
    username = forms.CharField(
        required=False
    )
    password = forms.CharField(
        required=False,
        widget = forms.PasswordInput
    )
    enable_password = forms.CharField(
        required=False,
        widget = forms.PasswordInput
    )

    class Meta:
        model = Credential
        fields = (
            'name', 'username', 'password', 'enable_password', 'tags',
        )


class CredentialCSVForm(NetBoxModelCSVForm):
    class Meta:
        model = Credential
        fields = ('name', 'username', 'password', 'enable_password')


class CredentialBulkEditForm(NetBoxModelBulkEditForm):
    username = forms.CharField(
        required=False
    )
    password = forms.CharField(
        required=False,
        widget = forms.PasswordInput
    )
    enable_password = forms.CharField(
        required=False,
        widget = forms.PasswordInput
    )

    model = Credential
    nullable_fields = ('username', 'password', 'enable_password')



#
# Discoverable views
#

class DiscoverableForm(NetBoxModelForm):
    address = forms.GenericIPAddressField()
    credential = forms.ModelChoiceField(
        queryset=Credential.objects.all(),
        required=True,
    )
    mode = forms.ChoiceField(
        choices=DiscoveryModeChoices,
        required=True
    )
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False
    )
    discoverable = forms.BooleanField(
        required=False,
        initial=True,
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        help_text='Site',
        required=True,
    )

    class Meta:
        model = Discoverable
        fields = (
            'address', 'device', 'credential', 'mode', 'discoverable', 'site', 'tags',
        )


class DiscoverableCSVForm(NetBoxModelCSVForm):
    address = forms.GenericIPAddressField(
        help_text='Management IP address',
    )
    credential = CSVModelChoiceField(
        queryset=Credential.objects.all(),
        required=True,
        to_field_name='name',
        help_text='Assigned credential',
    )
    mode = forms.ChoiceField(
        choices=DiscoveryModeChoices,
        required=True,
        help_text='Discovery mode',
    )
    site = CSVModelChoiceField(
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text='Site',
        required=True,
    )

    class Meta:
        model = Discoverable
        fields = ('address', 'credential', 'mode', 'site')


class DiscoverableBulkEditForm(NetBoxModelBulkEditForm):
    credential = CSVModelChoiceField(
        queryset=Credential.objects.all(),
        required=False,
        to_field_name='name',
        help_text='Assigned credential',
    )
    mode = forms.ChoiceField(
        choices=add_blank_choice(DiscoveryModeChoices),
        required=False,
        initial='',
        widget=StaticSelect(),
        help_text='Discovery mode',
    )
    discoverable = forms.NullBooleanField(
        help_text='Is discoverable?',
        required=False,
    )
    site = forms.ModelChoiceField(
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text='Site',
        required=False,
    )

    model = Discoverable
    nullable_fields = ('device')


class DiscoveryLogListFilterForm(NetBoxModelFilterSetForm):
    model = DiscoveryLog
    configuration = forms.NullBooleanField(
        required=False,
        label='Configuration output',
        widget=StaticSelect(
            choices=BOOLEAN_WITH_BLANK_CHOICES
        )
    )
    success = forms.NullBooleanField(
        required=False,
        label='Completed successfully',
        widget=StaticSelect(
            choices=BOOLEAN_WITH_BLANK_CHOICES
        )
    )
    parsed = forms.NullBooleanField(
        required=False,
        label='Parsed successfully',
        widget=StaticSelect(
            choices=BOOLEAN_WITH_BLANK_CHOICES
        )
    )
    ingested = forms.NullBooleanField(
        required=False,
        label='Ingested successfully',
        widget=StaticSelect(
            choices=BOOLEAN_WITH_BLANK_CHOICES
        )
    )
