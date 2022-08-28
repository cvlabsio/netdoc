from os.path import basename
import logging
import inspect
from slugify import slugify
from django.db.utils import IntegrityError
from . import functions

def ingest(log, force=False):
    """
    Processing show interface switchport.
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

    for item in log.parsed_output:
        # Parsing
        # https://github.com/networktocode/ntc-templates/tree/master/tests/cisco_ios/show_interfaces_switchport
        device_o = log.discoverable.device
        discoverable_o = log.discoverable
        interface_name = item['interface']
        site_o = log.discoverable.site
        mode = functions.normalize_switchport_mode(item['mode'])
        native_vlan=int(item["native_vlan"])
        trunking_vlans=functions.normalize_trunking_vlans(item["trunking_vlans"])
        access_vlan=int(item["access_vlan"])
        if mode == 'tagged' and len(trunking_vlans) == 4094:
            # Trunk with all VLANs
            args = {'mode': 'tagged-all'}
        elif mode == 'tagged':
            # Trunk with some VLANs
            vlan_o = functions.set_get_vlan(vid=access_vlan, site=site_o)
            args = {
                'mode': mode,
                'untagged_vlan': vlan_o,
            }
        else:
            # Access
            vlan_o = functions.set_get_vlan(vid=native_vlan, site=site_o)
            args = {
                'mode': mode,
                'untagged_vlan': vlan_o,
            }

        # Trusted data: we always update some data
        interface_o = functions.set_get_interface(label=interface_name, device=device_o, create_kwargs=args, update_kwargs=args)

        if force:
            # Clear all associated IP addresses
            interface_o.tagged_vlans.clear()

        if mode == 'tagged':
            # Add VLANs to the interface
            for vid in trunking_vlans:
                vlan_o = functions.set_get_vlan(vid=vid, site=site_o)
                try:
                    # VLAN already present
                    interface_o.tagged_vlans.get(pk=vlan_o.pk)
                except:
                    # Adding VLAN
                    interface_o.tagged_vlans.add(vlan_o)
            interface_o.save()

    # Update the log
    log.ingested = True
    log.save()
