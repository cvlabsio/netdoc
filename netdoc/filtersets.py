from netbox.filtersets import NetBoxModelFilterSet
from .models import Discoverable, Credential, DiscoveryLog, ArpTableEntry, MacAddressTableEntry, RouteTableEntry
from django.db.models import Q


class ArpTableEntryFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = ArpTableEntry
        fields = ()
        # fields = ('ip_address', 'mac_address', 'interface')

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(ip_address__icontains=value) |
            Q(mac_address__icontains=value) |
            Q(interface__name__icontains=value) |
            Q(interface__device__name__icontains=value) |
            Q(interface__device__device_role__name__icontains=value)
        )


class CredentialFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = Credential
        fields = ()
        # fields = ('name', 'username')

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) |
            Q(username__icontains=value)
        )


class DiscoverableFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = Discoverable
        fields = ()
        # fields = ('address', 'device', 'site', 'credential', 'mode')

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(address__icontains=value) |
            Q(device__name__icontains=value) |
            Q(site__name__icontains=value) |
            Q(credential__name__icontains=value) |
            Q(mode__icontains=value)
        )


class DiscoveryLogFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = DiscoveryLog
        fields = ('configuration', 'success', 'parsed', 'ingested')
        # fields = ('command', 'request', 'discoverable')

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(discoverable__address__icontains=value) |
            Q(discoverable__mode__icontains=value) |
            Q(discoverable__device__name__icontains=value) |
            Q(request__icontains=value) |
            Q(command__icontains=value)
        )


class MacAddressTableEntryFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = MacAddressTableEntry
        fields = ()
        # fields = ('mac_address', 'vvid', 'interface')

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(mac_address__icontains=value) |
            Q(interface__name__icontains=value) |
            Q(interface__device__name__icontains=value) |
            Q(interface__device__device_role__name__icontains=value)
        )


class RouteTableEntryFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = RouteTableEntry
        fields = ()

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(device__name__icontains=value) |
            Q(destination__icontains=value) |
            Q(type__icontains=value) |
            Q(nexthop_ip__icontains=value) |
            Q(nexthop_if__name__icontains=value) |
            Q(vrf__name__icontains=value)
        )
