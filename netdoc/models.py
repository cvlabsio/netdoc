from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel
from ipam.fields import IPAddressField
from dcim.fields import MACAddressField
from utilities.choices import ChoiceSet
from django.core.exceptions import ValidationError


class DiscoveryModeChoices(ChoiceSet):
    key = 'Discoverable.mode'

    CHOICES = [
        # ('netmiko_huawei', 'Netmiko Huawei'),
        ('netmiko_cisco_ios', 'Netmiko Cisco IOS'),
        ('netmiko_cisco_nxos', 'Netmiko Cisco NX-OS'),
        ('netmiko_cisco_xr', 'Netmiko Cisco XR'),
    ]


class RouteTypeChoices(ChoiceSet):
    key = 'RouteTableEntry.type'

    CHOICES = [
        ('u', 'Unknown'),
        ('c', 'Connected'),
        ('s', 'Static'),
        ('r', 'RIP'),
        ('e', 'EIGRP'),
        ('ex', 'EIGRP external'),
        ('oia', 'OSPF inter area'),
        ('on1', 'OSPF NSSA external type 1'),
        ('on2', 'OSPF NSSA external type 2'),
        ('oe1', 'OSPF external type 1'),
        ('oe2', 'OSPF external type 2'),
        ('i', 'IS-IS'),
        ('is', 'IS-IS summary'),
        ('i1', 'IS-IS level-1'),
        ('i2', 'IS-IS level-2'),
    ]

#
# ARPEntry model
#

class ArpTableEntry(NetBoxModel):
    """
    Model for ArpTableEntry. Each ARP seen on each network interface is
    counted. One IP Address can be associated to one MAC Address. One MAC
    Address can be associated to multiple IP Addresses.
    """
    interface = models.ForeignKey(
        to='dcim.Interface',
        on_delete=models.CASCADE,
        related_name='+',
        editable=False,
    )
    ip_address = IPAddressField(help_text='IPv4 address', editable=False)
    mac_address = MACAddressField(help_text='MAC Address', editable=False)
    vendor = models.CharField(
        max_length=255, blank=True, null=True, help_text='Vendor', editable=False
    )  #: Vendor (from OUI)

    class Meta:
        ordering = ('ip_address',)
        unique_together = ('interface', 'ip_address', 'mac_address')
        verbose_name = 'ARP table entry'
        verbose_name_plural = 'ARP table entries'

    def __str__(self):
        return f'{self.ip_address} has {self.mac_address} at {self.interface}'

    def get_absolute_url(self):
        return reverse('plugins:netdoc:arptable', args=[self.pk])


#
# Credential model
#

class Credential(NetBoxModel):
    name = models.CharField(
        max_length=100
    )
    username = models.CharField(
        max_length=100,
        blank=True,
    )
    password = models.CharField(
        max_length=100,
        blank=True,
    )
    enable_password = models.CharField(
        max_length=100,
        blank=True,
    )

    class Meta:
        ordering = ('name',)
        unique_together = ('name',)
        verbose_name = 'Credential'
        verbose_name_plural = 'Credentials'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netdoc:credential', args=[self.pk])


#
# Discoverable model
#

class Discoverable(NetBoxModel):
    address = models.GenericIPAddressField()
    device = models.OneToOneField(
        to='dcim.Device',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )
    credential = models.ForeignKey(
        to=Credential,
        on_delete=models.PROTECT,
        related_name='discoverables',
    )
    mode = models.CharField(
        max_length=30,
        choices=DiscoveryModeChoices,
    )
    discoverable = models.BooleanField(default=False) #: New created devices have discoverable=False by default (e.g. if created from CDP/LLDP)
    last_discovered_at = models.DateTimeField(blank=True, null=True, editable=False)
    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.CASCADE,
        related_name='+',
    )

    class Meta:
        ordering = ('mode', 'address')
        unique_together = ('address', 'mode')
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'

    def __str__(self):
        return f'{self.address} via {self.mode}'

    def get_absolute_url(self):
        return reverse('plugins:netdoc:discoverable', args=[self.pk])


#
# Discovery log model
#

class DiscoveryLog(NetBoxModel):
    command = models.CharField(max_length=255, editable=False)  #: Exact CMD line used in Netnmiko discovery
    configuration = models.BooleanField(
        default=False, editable=False,
    )
    discoverable = models.ForeignKey(
        to=Discoverable,
        on_delete=models.CASCADE,
        related_name='discoverylogs',
        editable=False,
    )
    parsed_output = models.JSONField(default=list, editable=False)
    raw_output = models.TextField(
        default="", blank=True, editable=False,
    )
    request = models.CharField(max_length=255, editable=False)  #: API request used in Netnmiko discovery (define the template parser)
    success = models.BooleanField(default=False, editable=False) # True if excuting request return OK and raw_output is valid (avoid command not found)
    parsed = models.BooleanField(default=False, editable=False)  #: True if parsing raw_output return a valid JSON
    ingested = models.BooleanField(default=False, editable=False)  #: True if all data are ingested without errors

    class Meta:
        ordering = ('created',)
        verbose_name = 'Log'
        verbose_name_plural = 'Logs'

    def __str__(self):
        return f'{self.request} at {self.created}'

    def get_absolute_url(self):
        return reverse('plugins:netdoc:discoverylog', args=[self.pk])


#
# MacAddressTableEntry model
#

class MacAddressTableEntry(NetBoxModel):
    """
    Model for MacAddressTableEntry. Each MAC Address seen on each network
    interface is counted. One IP Address can be associated to one AC
    Address. One MAC Address can be associated to multiple IP Addresses.
    """

    interface = models.ForeignKey(
        to='dcim.Interface',
        on_delete=models.CASCADE,
        related_name='+',
        editable=False,
    )
    mac_address = MACAddressField(help_text='MAC Address', editable=False)
    vendor = models.CharField(
        max_length=255, blank=True, null=True, help_text='Vendor', editable=False
    )  #: Vendor (from OUI)
    vvid = models.IntegerField(help_text="VLAN ID")  #: VLAN ID (TAG)

    class Meta:
        ordering = ('mac_address', 'vvid')
        unique_together = ('interface', 'mac_address', 'vvid')
        verbose_name = 'MAC Address table entry'
        verbose_name_plural = 'MAC Address table entries'

    def __str__(self):
        return f'{self.mac_address} is at {self.interface}'

    def get_absolute_url(self):
        return reverse('plugins:netdoc:macaddresstable', args=[self.pk])


#
# RouteTableEntry model
#

class RouteTableEntry(NetBoxModel):
    """
    Model for RouteTableEntry. Each route has a destination, type (connected, static...),
    nexthop_ip and/or nexthop_if, distance (administrative), metric. 
    """
    destination = IPAddressField(help_text='Destination network', editable=False)
    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        related_name='+',
    )
    distance = models.IntegerField(editable=False)
    metric = models.IntegerField(editable=False)
    nexthop_ip = IPAddressField(help_text='IPv4 address',
        editable=False,
        blank=True,
        null=True,)
    nexthop_if = models.ForeignKey(
        to='dcim.Interface',
        on_delete=models.CASCADE,
        related_name='+',
        editable=False,
        blank=True,
        null=True,
    )
    type = models.CharField(
        max_length=30,
        choices=RouteTypeChoices,
        editable=False,
    )
    vrf = models.ForeignKey(
        to='ipam.VRF',
        on_delete=models.CASCADE,
        related_name='+',
        editable=False,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ('device', 'type', 'metric')
        unique_together = ('device', 'destination', 'distance', 'metric', 'nexthop_if', 'nexthop_ip', 'type')
        verbose_name = 'Route '
        verbose_name_plural = 'Routes'

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('nexthop_ip') and not cleaned_data.get('nexthop_if'):  # This will check for None or Empty
            raise ValidationError({'nexthop_ip': 'Even one of nexthop_ip or nexthop_if should have a value.'})

    def __str__(self):
        if self.nexthop_ip:
            return f'{self.destination} [{self.distance}/{self.metric}] via {self.nexthop_ip}'
        else:
            # Assuming nexthop_if
            return f'{self.destination} [{self.distance}/{self.metric}] at {self.nexthop_if}'

    def get_absolute_url(self):
        return reverse('plugins:netdoc:routingtable', args=[self.pk])
