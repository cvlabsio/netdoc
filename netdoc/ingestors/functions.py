import re
import ipaddress
import logging
import importlib
from os.path import basename
from OuiLookup import OuiLookup
from slugify import slugify
from django.contrib.contenttypes.models import ContentType
from dcim.models import Device, DeviceType, DeviceRole, Manufacturer, Site, Platform, Interface, Cable, CablePath
from ipam.models import VRF, IPAddress, Prefix, VLAN
from netdoc.models import Discoverable, ArpTableEntry, MacAddressTableEntry, RouteTableEntry
from django.db.utils import IntegrityError
from django.db.models import Count
import macaddress

class AlreadyIngested(Exception):
    pass


class NotParsed(Exception):
    pass


class Postponed(Exception):
    pass


class WrongParser(Exception):
    pass


class NoIngestor(Exception):
    pass


#
# Setter and Getter
#


def set_get_arpentry(interface=None, ip_address=False, mac_address=None):
    """
    Create/Update and get an ARP table entry.

    Lookup: interface, ip_address, mac_address are unique
    """
    model = 'ArpTableEntry'

    mac_address = normalize_mac_address(mac_address)
    lookup_kwargs = {
        'interface': interface,
        'ip_address': ip_address,
        'mac_address': mac_address,
    }
    try:
        lookup_kwargs['vendor'] = list(OuiLookup().query(mac_address).pop().values()).pop()
    except:
        logging.error('Cannot get vendor, try to update with: ouilookup -u')
        pass

    arpentry_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs)
    # Update timestamp
    arpentry_o.save()

    return arpentry_o


def set_get_cable(left, right):
    """
    Create/Update and get a Cable.

    Lookup: ordered left, right are unique (tenants are not currenlty used)
    """
    # TODO: 1 if the interface is connected should skip
    # TODO: 2 if delete interface get some CablePathDoesNotExists

    interface_type = model_get_or_none('ContentType', model='interface')

    left_interface_o, right_interface_o = normalize_l2neighborship(left, right)
    lookup_kwargs = {
        'termination_a_id': left_interface_o.pk,
        'termination_b_id': right_interface_o.pk,
    }
    create_kwargs = {
        'termination_a_type': interface_type,
        'termination_b_type': interface_type,
    }

    cable_o=None
    try:
        cable_o = model_get_or_create(model_name='Cable', lookup_kwargs=lookup_kwargs, **create_kwargs)
    except IntegrityError:
        logging.error(f'Multiple neighbors on {left_interface_o} or {right_interface_o}')
        cable_o = None

    if cable_o:
        # Create CablePath
        lookup_cablepath_a_kwargs = {
            'origin_id': left_interface_o.pk,
            'destination_id': right_interface_o.pk,
        }
        lookup_cablepath_b_kwargs = {
            'origin_id': right_interface_o.pk,
            'destination_id': left_interface_o.pk,
        }
        create_cablepath_kwargs = {
            'path': [cable_o],
            'origin_type': interface_type,
            'destination_type': interface_type
        }
        cable_path_a_o = model_get_or_create(model_name='CablePath', lookup_kwargs=lookup_cablepath_a_kwargs, **create_cablepath_kwargs)
        cable_path_b_o = model_get_or_create(model_name='CablePath', lookup_kwargs=lookup_cablepath_b_kwargs, **create_cablepath_kwargs)

    return cable_o


def set_get_device(name=None, create=False, create_kwargs=None, update_kwargs=None):
    """
    Create/Update and get a Device.

    Lookup: name is unique (tenants are not currenlty used)
    Create: site is mandatory
    """
    if not create_kwargs:
        create_kwargs = {}
    if not update_kwargs:
        update_kwargs = {}

    model = 'Device'

    # Requirements
    if 'manufacturer' in create_kwargs and 'device_type' in create_kwargs:
        # Using the given device_type and manufacturer
        manufacturer_slug = slugify(create_kwargs['manufacturer'])
        device_type_slug = slugify(create_kwargs['device_type'])
        device_type_o = set_get_device_type(slug=f'{manufacturer_slug}-{device_type_slug}', create_kwargs={'name':create_kwargs['device_type'], 'manufacturer':create_kwargs['manufacturer']})
    elif 'manufacturer' in create_kwargs and 'device_type' not in create_kwargs:
        # Using the default device_type for a given manufacturer
        device_type_o = set_get_device_type(create_kwargs={'manufacturer':create_kwargs['manufacturer']})
    elif 'manufacturer' not in create_kwargs and 'device_type' in create_kwargs:
        # Using the default manufacturer for a given device_type
        device_type_o = set_get_device_type(create_kwargs={'name':create_kwargs['device_type']})
    else:
        # Using the default device_type/manufacturer
        device_type_o = set_get_device_type()
    device_role_o = set_get_device_role()

    name = normalize_hostname(name)
    lookup_kwargs = {
        'name': name,
    }
    create_kwargs['device_type'] = device_type_o
    create_kwargs['device_role'] = device_role_o
    create_kwargs['status'] = 'active'
    create_kwargs.pop('manufacturer', None)

    device_o = model_get_or_none(model_name=model, **lookup_kwargs)
    if not device_o and (create_kwargs or create):
        device_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs, **create_kwargs)
    elif device_o and update_kwargs:
        model_get_and_update(device_o, **update_kwargs)
    return device_o


def set_get_discoverable(address=None, device=None, site=None, force=False, **kwargs):
    """
    Create/Update and get a Discoverable.

    Lookup: address, site are unique (tenants are not currenlty used)
    Create: address, device, site is mandatory

    Device can be missing in the stored Discoverable if they are manually created.
    """
    model = 'Discoverable'

    discoverable_o = None

    try:
        # Discoverable with same address and Device already exists
        discoverable_o = Discoverable.objects.get(address=address, device=device, site=site)
        return discoverable_o
    except Discoverable.DoesNotExist:
        pass

    try:
        # Discoverable with same address exists
        discoverable_o = Discoverable.objects.get(address=address, site=site)
    except Discoverable.DoesNotExist:
        discoverable_o = None

    # Duplicated discoverable with same device exists
    duplicated_discoverable_o = Discoverable.objects.filter(device=device, site=site).exclude(address=address).first()

    if discoverable_o and duplicated_discoverable_o:
        # Discoverable exist but Device is assigned to another Discoverable
        if force:
            # discoverable_o takes precedence
            duplicated_discoverable_o.device = None
            duplicated_discoverable_o.save()
            discoverable_o.device = device
            discoverable_o.save()
            return discoverable_o
        else:
            # duplicated_discoverable_o takes precedence
            return duplicated_discoverable_o
    elif discoverable_o and not duplicated_discoverable_o:
        # Discoverable exists without Device
        discoverable_o.device = device
        discoverable_o.save()
        return discoverable_o
    elif not discoverable_o and duplicated_discoverable_o:
        # Discoverable not exist but Device is assinged to a different Discoverable
        if force:
            # discoverable_o takes precedence
            duplicated_discoverable_o.device = None
            duplicated_discoverable_o.save()
        else:
            # duplicated_discoverable_o takes precedence
            return duplicated_discoverable_o

    # Discoverable with same Device and address not found
    if address and site:
        discoverable_o = Discoverable.objects.create(device=device, site=site, address=address, **kwargs)
    return discoverable_o


def set_get_device_role(slug=None, create=False, create_kwargs=None, update_kwargs=None):
    """
    Create/Update and get a DeviceRole.

    Lookup: slug is unique
    Create: name, is mandatory

    A DeviceRole is a group of devices with the same role:
    - Leaf/Spine switches
    - Access switches
    - Border routers
    - ...
    During the discovery Unknown is used.
    """
    model = 'DeviceRole'

    if not create_kwargs:
        create_kwargs = {}
    if not update_kwargs:
        update_kwargs = {}

    if slug:
        # Slug is set
        pass
    elif 'name' in create_kwargs:
        # Setting slug from name
        slug = slugify(create_kwargs['name'])
    else:
        # Slug and name not set
        slug = 'unknown'
        create_kwargs['name'] = 'Unknown'

    if 'color' not in create_kwargs:
        # Set default color
        create_kwargs['color'] = '9e9e9e'

    lookup_kwargs = {'slug': slug}

    device_role_o = model_get_or_none(model_name=model, **lookup_kwargs)
    if not device_role_o and (create_kwargs or create):
        device_role_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs, **create_kwargs)
    elif device_role_o and update_kwargs:
        model_get_and_update(device_role_o, **update_kwargs)
    return device_role_o


def set_get_device_type(slug=None, create=False, create_kwargs=None, update_kwargs=None):
    """
    Create/Update and get a DeviceType.

    Lookup: slug is unique built as '{manufacturer}-{type}'
    Create: none

    A DeviceType refers to the device model.
    During the discovery Unknown is used.
    """
    model = 'DeviceType'

    if not create_kwargs:
        create_kwargs = {}
    if not update_kwargs:
        update_kwargs = {}

    # Requirements
    if not slug:
        if 'manufacturer' in create_kwargs:
            # Forcing slug from name and manufacturer
            manufacturer_o = set_get_manufacturer(create_kwargs={'name': create_kwargs['manufacturer']})
            create_kwargs['manufacturer'] = manufacturer_o
        else:
            # Using the default manufacturer
            manufacturer_o = set_get_manufacturer()
            create_kwargs['manufacturer'] = manufacturer_o
        if 'model' in create_kwargs:
            # Forcing slug from model
            slug = f'{slugify(create_kwargs["model"])}-{manufacturer_o.slug}'
        else:
            # Slug and model not set
            slug = 'unknown'
            create_kwargs['model'] = 'Unknown'

    lookup_kwargs = {'slug': slug}

    device_type_o = model_get_or_none(model_name=model, **lookup_kwargs)
    if not device_type_o and (create_kwargs or create):
        device_type_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs, **create_kwargs)
    elif device_type_o and update_kwargs:
        model_get_and_update(device_type_o, **update_kwargs)
    return device_type_o


def set_get_interface(device=None, label=None, create=False, create_kwargs=None, update_kwargs=None):
    """
    Create/Update and get an Interface.

    lookup: label and device
    Create: name is mandatory
    """
    model = 'Interface'

    if not create_kwargs:
        create_kwargs = {}
    if not update_kwargs:
        update_kwargs = {}

    label = short_interface_name(label)
    lookup_kwargs = {
        'label': label,
        'device': device,
    }

    interface_o = model_get_or_none(model_name=model, **lookup_kwargs)
    if not interface_o and create_kwargs and 'type' not in create_kwargs:
        # If interface does not exist, using other as default type
        create_kwargs['type'] = 'other'

    if not interface_o and (create_kwargs or create):
        interface_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs, **create_kwargs)
    elif interface_o and update_kwargs:
        model_get_and_update(interface_o, **update_kwargs)
    return interface_o


def set_get_ip_address(address=None, create=False, create_kwargs=None, update_kwargs=None):
    """
    Create/Update and get a IPAddress.

    Lookup: address is unique
    Create: vrf is optional
    """
    model = 'IPAddress'

    if not create_kwargs:
        create_kwargs = {}
    if not update_kwargs:
        update_kwargs = {}

    lookup_kwargs = {'address': address}

    ipaddress_o = model_get_or_none(model_name=model, **lookup_kwargs)
    if not ipaddress_o and (create_kwargs or create):
        ipaddress_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs, **create_kwargs)
    elif ipaddress_o and update_kwargs:
        model_get_and_update(ipaddress_o, **update_kwargs)
    return ipaddress_o


def set_get_macaddressentry(interface=None, vvid=False, mac_address=None):
    """
    Create/Update and get a MAC Address table entry.

    Lookup: interface, vvid, mac_address are unique
    """
    model = 'MacAddressTableEntry'

    mac_address = normalize_mac_address(mac_address)
    try:
        vvid = int(vvid)
    except:
        vvid = 0
    lookup_kwargs = {
        'interface': interface,
        'vvid': vvid,
        'mac_address': mac_address,
    }
    try:
        lookup_kwargs['vendor'] = list(OuiLookup().query(mac_address).pop().values()).pop()
    except:
        logging.error('Cannot get vendor, try to update with: ouilookup -u')
        pass

    macaddressentry_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs)
    # Update timestamp
    macaddressentry_o.save()

    return macaddressentry_o


def set_get_manufacturer(slug=None, create=False, create_kwargs=None, update_kwargs=None):
    """
    Create/Update and get a Manufacturer.

    Lookup: slug is unique
    Create: none

    A Manufacturer is reffered by DeviceType.
    """
    model = 'Manufacturer'

    if not create_kwargs:
        create_kwargs = {}
    if not update_kwargs:
        update_kwargs = {}

    if slug:
        # Slug is set
        pass
    elif 'name' in create_kwargs:
        # Setting slug from name
        slug = slugify(create_kwargs['name'])
    else:
        # Slug and name not set
        slug = 'unknown'
        create_kwargs['name'] = 'Unknown'

    lookup_kwargs = {'slug': slug}

    manufacturer_o = model_get_or_none(model_name=model, **lookup_kwargs)
    if not manufacturer_o and (create_kwargs or create):
        manufacturer_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs, **create_kwargs)
    elif manufacturer_o and update_kwargs:
        model_get_and_update(manufacturer_o, **update_kwargs)
    return manufacturer_o


def set_get_prefix(prefix=None, create=False, create_kwargs=None, update_kwargs=None):
    """
    Create/Update and get a Prefix.

    Lookup: prefix is unique
    Create: vrf, site are optionals
    """
    model = 'Prefix'

    if not create_kwargs:
        create_kwargs = {}
    if not update_kwargs:
        update_kwargs = {}

    lookup_kwargs = {'prefix': prefix}

    prefix_o = model_get_or_none(model_name=model, **lookup_kwargs)
    if not prefix_o and (create_kwargs or create):
        prefix_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs, **create_kwargs)
    elif prefix_o and update_kwargs:
        model_get_and_update(prefix_o, **update_kwargs)
    return prefix_o



def set_get_route(device=None, destination=None, distance=None, metric=None, nexthop_ip=None, nexthop_if=None, type=None, vrf=None):
    """
    Create/Update and get a Route.

    Lookup: device, destination, distance, metric, nexthop_ip, nexthop_if, type, vrf are unique
    """
    model = 'RouteTableEntry'
    type = normalize_routetype(type)
    lookup_kwargs = {
        'device': device,
        'destination': destination,
        'type': type,
        'vrf': vrf,
    }
    if nexthop_ip:
        lookup_kwargs['nexthop_ip'] = nexthop_ip
    if nexthop_if:
        lookup_kwargs['nexthop_if'] = nexthop_if

    try:
        lookup_kwargs['metric'] = int(metric)
    except:
        if type == 'c':
            lookup_kwargs['metric'] = 0
        else:
            lookup_kwargs['metric'] = 256
    try:
        lookup_kwargs['distance'] = int(distance)
    except:
        if type == 'c':
            lookup_kwargs['distance'] = 0
        elif type == 's':
            lookup_kwargs['distance'] = 1
        else:
            lookup_kwargs['distance'] = 256

    route_o = model_get_or_none(model_name=model, **lookup_kwargs)
    if not route_o:
        route_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs)
    return route_o


def set_get_vlan(vid=None, name=None, site=None, create=False, create_kwargs=None, update_kwargs=None):
    """
    Create/Update and get a VLAN.

    Lookup: vid, name, site are unique
    Create: name is mandatory
    """
    model = 'VLAN'

    if not create_kwargs:
        create_kwargs = {}
    if not update_kwargs:
        update_kwargs = {}

    if name:
        lookup_kwargs = {'vid': vid, 'name': name, 'site': site}
        
        if not 'status' in create_kwargs:
            # Set default status
            create_kwargs['status'] = 'active'

        vlan_o = model_get_or_none(model_name=model, **lookup_kwargs)
        if not vlan_o and (create_kwargs or create):
            vlan_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs, **create_kwargs)
        elif vlan_o and update_kwargs:
            model_get_and_update(vlan_o, **update_kwargs)
    else:
        # Getting the first vlan matching vid and site
        vlan_o = VLAN.objects.filter(vid=vid, site=site).exclude(name='TBD').first()
        if not vlan_o:
            # VLAN does not exist, finding a placeholder
            vlan_o = VLAN.objects.filter(vid=vid, site=site).first()
        if not vlan_o:
            # VLAN does not exist, creating a placeholder
            vlan_o = VLAN.objects.create(vid=vid, site=site, name='TBD')

    return vlan_o


def set_get_vrf(name=None, create=False, create_kwargs=None, update_kwargs=None):
    """
    Create/Update and get a VRF.

    Lookup: name is unique
    Create: none
    """
    model = 'VRF'

    if not create_kwargs:
        create_kwargs = {}
    if not update_kwargs:
        update_kwargs = {}

    lookup_kwargs = {'name': name}

    vrf_o = model_get_or_none(model_name=model, **lookup_kwargs)
    if not vrf_o and (create_kwargs or create):
        vrf_o = model_get_or_create(model_name=model, lookup_kwargs=lookup_kwargs, **create_kwargs)
    elif vrf_o and update_kwargs:
        model_get_and_update(vrf_o, **update_kwargs)
    return vrf_o


#
# Helper functions
#

def delete_none(_dict):
    """
    Delete None values recursively from all of the dictionaries.
    """
    for key, value in list(_dict.items()):
        if isinstance(value, dict):
            delete_none(value)
        elif value is None:
            del _dict[key]
        elif isinstance(value, list):
            for v_i in value:
                if isinstance(v_i, dict):
                    delete_none(v_i)
    return _dict


def log_ingest(log):
    function_name = parsing_function_from_log(log)
    try:
        m = importlib.import_module(f'netdoc.ingestors.{function_name}')
    except:
        raise NoIngestor
    m.ingest(log, force=True)
    return log


def model_get_and_update(obj, **kwargs):
    """
    Update and get a generic Model object using kwargs.
    """
    for key, value in kwargs.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def model_get_or_create(model_name=None, lookup_kwargs=None, **kwargs):
    """
    Get or create a generic Model object using kwargs.
    """
    obj = None
    kwargs = delete_none(kwargs)

    model = eval(f'{model_name}')
    model_not_found = eval(f'{model_name}.DoesNotExist')

    try:
        obj = model.objects.get(**lookup_kwargs)
    except model_not_found:
        logging.info(f'{model_name} not found for {lookup_kwargs}')
        obj = model.objects.create(**lookup_kwargs, **kwargs)
    return obj


def model_get_or_none(model_name=None, **kwargs):
    """
    Get a generic Model object using slug or return None.
    """
    model = eval(f'{model_name}')
    model_not_found = eval(f'{model_name}.DoesNotExist')

    try:
        o = model.objects.get(**kwargs)
    except model_not_found:
        return None
    return o


def normalize_interface_duplex(duplex):
    """
    Normalize Interface.duplex.
    """
    duplex = duplex.lower()
    if 'auto' in duplex:
        return 'auto'
    elif 'half' in duplex:
        return 'half'
    elif 'full' in duplex:
        return 'full'
    return None


def normalize_hostname(name):
    """
    Hostnames must be uppercase without domain.
    """
    if name:
        try:
            # Check if it's a valid IP Address
            ipaddress.ip_address(name)
            return name
        except:
            pass
        name = name.split('.')[0]  # Removes domain if exists
        name = name.upper()
        name = re.sub(r'\(.+?\)', '', name)  # NX-OS: remove serial number (e.g. hostname(serialnumber))
    return name


def normalize_interface_bandwidth(bandwidth):
    """
    Normalize Interface speed.
    """
    bandwidth = bandwidth.lower()
    bandwidth = bandwidth.replace(' ', '')
    bandwidth = bandwidth.replace('kbit', '')
    bandwidth = bandwidth.replace('mbps', '000')
    bandwidth = bandwidth.replace('mb/s', '000')
    bandwidth = bandwidth.replace('gb/s', '000000')
    return bandwidth


def normalize_l2neighborship(left_interface, right_interface):
    """
    Neighborship must be sorted by hostname.
    """
    if left_interface.device.name < right_interface.device.name:
        # Hostname comparison
        return left_interface, right_interface
    elif left_interface.device.name > right_interface.device.name:
        # Hostname comparison
        return right_interface, left_interface
    elif left_interface.name < right_interface.name:
        return left_interface, right_interface
    # Interface names cannot be equal
    return right_interface, left_interface


def normalize_mac_address(mac_address):
    """
    MAC Address must be in the format 01:23:45:67:89:AB
    """
    mac_address_o = macaddress.MAC(mac_address)
    return str(mac_address_o).replace("-", ":")


def normalize_protocol(protocol):
    return protocol.lower()


def normalize_routetype(route_type):
    route_type = route_type.lower()
    if route_type in ['c', 'direct', 'local', 'hsrp', 'l']:
        # Connected
        return 'c'
    elif route_type in ['s', 'static']:
        # Static
        return 's'
    elif route_type in ['r', 'rip-10']:
        # RIP
        return 'r'
    elif route_type in ['b']:
        # BGP
        return 'b'
    elif route_type in ['d']:
        # EIGRP
        return 'e'
    elif route_type in ['ex']:
        # EIGRP External
        return 'ex'
    elif route_type in ['o']:
        # OSPF Inter Area
        return 'oia'
    elif route_type in ['n1']:
        # OSPF NSSA Type 1
        return 'on1'
    elif route_type in ['n2']:
        # OSPF NSSA Type 2
        return 'on2'
    elif route_type in ['e1']:
        # OSPF External Type 1
        return 'oe1'
    elif route_type in ['e2']:
        # OSPF External Type 2
        return 'oe2'
    elif route_type in ['i']:
        # IS-IS
        return 'i'
    elif route_type in ['su']:
        # IS-IS Summary
        return 'is'
    elif route_type in ['l1']:
        # IS-IS L1
        return 'i1'
    elif route_type in ['l2']:
        # IS-IS
        return 'i2'
    print(route_type)
    return 'u'


def normalize_switchport_mode(switchport_mode):
    """
    Normalize Interface.switchport_mode.
    """
    switchport_mode = switchport_mode.lower()
    if 'trunk' in switchport_mode:
        return 'tagged'
    elif 'access' in switchport_mode:
        return 'access'
    elif switchport_mode == 'fex-fabric':
        return 'tagged-all'
    elif 'private-vlan' in switchport_mode:
        return 'tagged'
    elif switchport_mode == 'down':
        # Ignore down interfaces
        return 'access'
    else:
        logging.warning(f'cannot parse switchport_mode {switchport_mode}')
        return 'access'


def normalize_trunking_vlans(trunking_vlans):
    """
    Normalize a VLAN list (can be a comma separated string or a list)
    """
    vlans = []
    if isinstance(trunking_vlans, list):
        for vlan in trunking_vlans:
            vlans.extend(normalize_vlan(vlan))
    else:
        vlans.extend(normalize_vlan(trunking_vlans))
    return vlans


def normalize_vlan(vlan):
    """
    Normalize a single VLAN or VLAN range, returning a list of integer.
    """
    if isinstance(vlan, int):
        # Integer
        return [vlan]

    vlan = vlan.lower()
    vlan = vlan.replace(' ', '')
    if vlan == 'all':
        # All VLANs
        return normalize_vlan('1-4094')
    elif ',' in vlan:
        # Set of VLANs (must before VLAN range)
        vlans = []
        for v in vlan.split(','):
            vlans.extend(normalize_vlan(v))
        return vlans
    elif '-' in vlan:
         # VLAN range
        try:
            return list(range(int(vlan.split('-')[0]), int(vlan.split('-')[1]) + 1))
        except:
            logging.warning(f'cannot convert VLAN {vlan} range to integer')
            pass
    else:
        try:
            return [int(vlan)]
        except:
            logging.warning(f'cannot convert VLAN {vlan} to integer')
            pass
    return []


def parent_interface(label):
    label = short_interface_name(label)
    if re.match(r"^[^.]+\.[0-9]+$", label):
        # Contains only one "." and ends with numbers
        parent_label = re.sub(r".[0-9]+$", "", label)
        return parent_label
    return None


def physical_interface(label):
    label = short_interface_name(label)
    if re.match(r"^(e|gi|te|vmnic|mgmt).*", label):
        # Physical (ethernet, gigabit, tengigabit, vmnic)
        return True
    elif re.match(r"^[0-9]+", label):
        # Physical (interface with only numbers)
        return True
    return False


def parsing_function_from_log(log):
    function_name = f"{log.discoverable.mode}_{log.request}"
    function_name = function_name.replace(' ', '_')
    function_name = function_name.replace('-', '_')
    return function_name


# def interface_type(shortname):
#     """
#     Return interface type from shortname.
#     """
#     shortname = short_interface_name(shortname)
#     if re.match(r"^(po|bond).*", shortname):
#         # LAG (portchannel, bond)
#         return "lag"
#     elif re.match(r"lo.*", shortname):
#         # Loopback
#         return "virtual"
#     elif re.match(r"tun.*", shortname):
#         # Tunnel
#         return "virtual"
#     elif re.match(r"vl.*", shortname):
#         # SVI (VLAN interface)
#         return "bridge"
#     elif re.match(r"null.*", shortname):
#         # Null
#         return "virtual"
#     else:
#         return "other"


def short_interface_name(name):
    """
    Given an interface name, return the shortname.
    """
    name = name.lower()
    if name.startswith("gigabitethernet"):
        return name.replace("gigabitethernet", "gi")
    elif name.startswith("tengigabitethernet"):
        return name.replace("tengigabitethernet", "te")
    elif name.startswith("ethernet"):
        return name.replace("ethernet", "e")
    elif name.startswith("eth"):
        return name.replace("eth", "e")
    elif name.startswith("et"):
        return name.replace("et", "e")
    elif name.startswith("vlan"):
        return name.replace("vlan", "vl")
    elif name.startswith("management"):
        return name.replace("management", "mgmt")
    elif name.startswith("loopback"):
        return name.replace("loopback", "lo")
    elif name.startswith("port-channel"):
        return name.replace("port-channel", "po")
    else:
        return name