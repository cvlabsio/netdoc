from rest_framework import serializers

from ipam.api.serializers import NestedPrefixSerializer
from dcim.api.serializers import NestedDeviceSerializer
from netbox.api.serializers import NetBoxModelSerializer, WritableNestedSerializer
from ..models import Credential, Discoverable, DiscoveryLog, ArpTableEntry, MacAddressTableEntry, RouteTableEntry 


#
# Nested serializers
#

class NestedCredentialSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netdoc-api:credential-detail'
    )

    class Meta:
        model = Credential
        fields = (
            'id', 'url', 'name', 'username',
        )


class NestedDiscoverableSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netdoc-api:discoverable-detail'
    )

    class Meta:
        model = Discoverable
        fields = (
            'id', 'url', 'address', 'device', 'mode'
        )

#
# Regular serializers
#

class ArpTableEntrySerializer(NetBoxModelSerializer):
    # Used only for delete
    class Meta:
        model = ArpTableEntry
        fields = '__all__'


class CredentialSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netdoc-api:credential-detail'
    )
    discoverables_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Credential
        fields = (
            'id', 'url', 'name', 'username', 'discoverables_count',
        )


class DiscoverableSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netdoc-api:discoverable-detail'
    )
    discoverylogs_count = serializers.IntegerField(read_only=True)
    credential = NestedCredentialSerializer()
    device = NestedDeviceSerializer()

    class Meta:
        model = Discoverable
        fields = (
            'id', 'url', 'address', 'device', 'credential', 'mode', 'discoverylogs_count'
        )


class DiscoveryLogSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netdoc-api:discoverylog-detail'
    )
    discoverable = NestedDiscoverableSerializer()

    class Meta:
        model = DiscoveryLog
        fields = (
            'id', 'url', 'discoverable', 'configuration', 'parsed_output', 'raw_output', 'request', 'success', 'parsed', 'ingested'
        )


class RouteTableEntrySerializer(NetBoxModelSerializer):
    # Used only for delete
    class Meta:
        model = RouteTableEntry
        fields = '__all__'


class MacAddressTableEntrySerializer(NetBoxModelSerializer):
    # Used only for delete
    class Meta:
        model = MacAddressTableEntry
        fields = '__all__'
