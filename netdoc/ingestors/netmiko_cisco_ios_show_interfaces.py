from os.path import basename
import logging
import inspect
from slugify import slugify
from . import functions

def ingest(log, force=False):
    """
    Processing show interfaces.
    """
    function_name = ''.join(basename(__file__).split('.')[0])
    if function_name != functions.parsing_function_from_log(log):
        raise functions.WrongParser(f'Cannot use {function_name} for log {log.pk}')
    if not log.parsed:
        raise functions.NotParsed(f'Skipping unparsed log {log.pk}')
    if not log.parsed_output:
        raise functions.NotParsed(f'Skipping empty parsed log {log.pk}')
    if not force and log.ingested:
        raise functions.AlreadyIngested(f'Skipping injested log {log.pk}')
    if not log.discoverable.device:
        raise functions.Postponed(f'Device is required, postponing {log.pk}')

    site_o = log.discoverable.site

    for item in log.parsed_output:
        # Parsing
        # https://github.com/networktocode/ntc-templates/tree/master/tests/cisco_ios/show_interfaces
        device_o = log.discoverable.device
        interface_name = item['interface']
        if item['link_status'] == 'deleted':
            # Skipping deleted interface
            continue
        args = {
            'description': item['description'],
            'duplex': functions.normalize_interface_duplex(item['duplex']),
            'speed': functions.normalize_interface_bandwidth(item['bandwidth']),
            'name': interface_name,
            'mac_address': item['address'],
        }
        if item['encapsulation'] == '802.1Q Virtual LAN' and item['vlan_id']:
            # Interface is configured to read 802.1Q
            vlan_o = functions.set_get_vlan(vid=item['vlan_id'], site=site_o)
            args['mode'] = functions.normalize_switchport_mode('trunk')
            args['untagged_vlan'] = vlan_o

        try:
            args['mtu'] = int(item['mtu'])
        except ValueError:
            pass

        interface_parent = functions.parent_interface(interface_name)
        if interface_parent:
            args['parent'] = functions.set_get_interface(label=interface_parent, device=device_o)

        # Trusted data: we always update some data
        interface_o = functions.set_get_interface(label=interface_name, device=device_o, create_kwargs=args, update_kwargs=args)
 
    # Update the log
    log.ingested = True
    log.save()
