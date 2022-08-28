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
        site_o = log.discoverable.device.site
        device_o = log.discoverable.device
        ip_address = item['address']
        mac_address = item['mac']
        interface_name = item['interface']

        interface_o = functions.set_get_interface(label=interface_name, device=device_o, create_kwargs={'name': interface_name})
        arpentry_o = functions.set_get_arpentry(interface=interface_o, ip_address=ip_address, mac_address=mac_address)


    # Update the log
    log.discoverable.save()
    log.ingested = True
    log.save()
