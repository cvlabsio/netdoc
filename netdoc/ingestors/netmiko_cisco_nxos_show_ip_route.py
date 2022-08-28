from os.path import basename
import logging
import inspect
from slugify import slugify
from . import functions

def ingest(log, force=False):
    """
    Processing show vlan.
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
        # https://github.com/networktocode/ntc-templates/tree/master/tests/cisco_ios/show_ip_arp
        vrf_name = item['vrf']
        device_o = log.discoverable.device
        interface_name = item['nexthop_if']

        args = {
            'device': device_o,
            'distance': item['distance'],
            'destination': f"{item['network']}/{item['mask']}",
            'metric': item['metric'],
            'type': item['protocol'],
        }

        if item['nexthop_if']:
            args['nexthop_if'] = functions.set_get_interface(label=interface_name, device=device_o, create_kwargs={'name': interface_name})
        if item['nexthop_ip']:
            args['nexthop_ip'] = item['nexthop_ip']
        if vrf_name:
            vrf_o = functions.set_get_vrf(name=vrf_name, create_kwargs={})
            args['vrf'] = vrf_o
        
        route_o = functions.set_get_route(**args)

    # Update the log
    log.discoverable.save()
    log.ingested = True
    log.save()
