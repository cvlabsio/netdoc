import django_tables2 as tables
from django.urls import reverse

from netbox.tables import NetBoxTable, ChoiceFieldColumn
from netbox.tables.columns import ActionsItem, ActionsColumn
from utilities.utils import get_viewname
from . import models


#
# ArpTableEntry tables
#

class ArpTableEntryTable(NetBoxTable):
    device = tables.Column(accessor='interface.device')
    device_role = tables.Column(accessor='interface.device.device_role')
    actions = ()

    class Meta(NetBoxTable.Meta):
        model = models.ArpTableEntry
        fields = ('pk', 'id', 'ip_address', 'mac_address', 'vendor', 'device_role', 'device', 'interface', 'last_updated')
        default_columns = ('ip_address', 'mac_address', 'vendor', 'device_role', 'device', 'interface', 'last_updated')


#
# Credential tables
#

class CredentialTable(NetBoxTable):
    name = tables.Column(
        linkify=True
    )
    discoverables_count = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = models.Credential
        fields = ('pk', 'id', 'username', 'discoverables_count')
        default_columns = ('name', 'username', 'discoverables_count')


#
# Discoverable tables
#

class DiscoverableTable(NetBoxTable):
    address = tables.Column(
        linkify=True
    )
    mode = ChoiceFieldColumn()
    discoverylogs_count = tables.Column()
    discovery_button = """
    <a class="btn btn-sm btn-secondary" href="{% url 'plugins:netdoc:discoverable_discover' pk=record.pk %}" title="Discover">
        <i class="mdi mdi-refresh"></i>
    </a>
    """
    actions = ActionsColumn(extra_buttons=discovery_button)

    class Meta(NetBoxTable.Meta):
        model = models.Discoverable
        fields = ('pk', 'id', 'address', 'device', 'site', 'credential', 'mode', 'discoverable', 'last_discovered_at', 'discoverylogs_count')
        default_columns = ('address', 'device', 'site', 'credential', 'mode', 'discoverable', 'last_discovered_at', 'discoverylogs_count')


#
# Discovery log tables
#

class DiscoveryLogTable(NetBoxTable):
    actions = ActionsColumn(actions=('delete', )) # Read only objects
    device = tables.Column(accessor='discoverable.device')

    class Meta(NetBoxTable.Meta):
        model = models.DiscoveryLog
        fields = ('pk', 'id', 'created', 'discoverable', 'device', 'request', 'command', 'configuration', 'success', 'parsed', 'ingested')
        default_columns = ('id', 'created', 'discoverable', 'device', 'request', 'command', 'configuration', 'success', 'parsed', 'ingested')


#
# MacAddressTableEntry tables
#

class MacAddressTableEntryTable(NetBoxTable):
    device = tables.Column(accessor='interface.device')
    device_role = tables.Column(accessor='interface.device.device_role')
    actions = ()

    class Meta(NetBoxTable.Meta):
        model = models.MacAddressTableEntry
        fields = ('pk', 'id', 'mac_address', 'vvid', 'vendor', 'device_role', 'device', 'interface', 'last_updated')
        default_columns = ('mac_address', 'vvid', 'vendor', 'device_role', 'device', 'interface', 'last_updated')



#
# RouteTableEntry tables
#

class RouteTableEntryTable(NetBoxTable):
    actions = ()

    class Meta(NetBoxTable.Meta):
        model = models.RouteTableEntry
        fields = ('pk', 'id', 'device', 'destination', 'type', 'distance', 'metric', 'nexthop_ip', 'nexthop_if', 'vrf', 'last_updated')
        default_columns = ('device', 'destination', 'type', 'distance', 'metric', 'nexthop_ip', 'nexthop_if', 'vrf', 'last_updated')
