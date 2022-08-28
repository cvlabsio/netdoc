from os.path import basename
import logging
import inspect
from slugify import slugify
from django.db.utils import IntegrityError
from . import functions

def ingest(log, force=False):
    """
    Processing show cdp neighbors detail.
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
        # https://github.com/networktocode/ntc-templates/tree/master/tests/cisco_nxos/show_cdp_neighbors_detail            # Get interface
        device_o = log.discoverable.device
        discoverable_o = log.discoverable
        interface_name = item['local_port']
        remote_interface_name = item['remote_port']
        remote_address = item['mgmt_ip']
        remote_device_name = item['dest_host']
        site = log.discoverable.site

        # Excluding non physical interfaces
        if not functions.physical_interface(interface_name) and not functions.physical_interface(remote_interface_name):
            logging.warning(f'Excluding non physical interfaces {interface_name} or {remote_interface_name}')
            continue

        remote_device_o = functions.set_get_device(name=remote_device_name, create_kwargs={'site': site})
        interface_o = functions.set_get_interface(label=interface_name, device=device_o, create_kwargs={'name': interface_name})
        remote_interface_o = functions.set_get_interface(label=remote_interface_name, device=remote_device_o, create_kwargs={'name': remote_interface_name})
        remote_discoverable_o = functions.set_get_discoverable(address=remote_address, device=remote_device_o, site=site, mode=discoverable_o.mode, credential=discoverable_o.credential)
        cable_o = functions.set_get_cable(interface_o, remote_interface_o)
 
    # Update the log
    log.ingested = True
    log.save()
