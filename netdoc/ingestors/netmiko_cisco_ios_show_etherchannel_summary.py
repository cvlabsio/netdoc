from os.path import basename
import logging
import inspect
from slugify import slugify
from . import functions

def ingest(log, force=False):
    """
    Processing show etherchannel summary.
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
        # https://github.com/networktocode/ntc-templates/tree/master/tests/cisco_ios/show_etherchannel_summary
        device_o = log.discoverable.device
        bundle_name = item['po_name']
        physical_interfaces = item['interfaces']

        args = {'type': 'lag'}

        # Trusted data: we always update some data
        bundle_o = functions.set_get_interface(label=bundle_name, device=device_o, create_kwargs=args, update_kwargs=args)
        for physical_interface in physical_interfaces:
            attached_args = {'lag': bundle_o}
            # Trusted data: we always update some data
            physical_interface_o = functions.set_get_interface(label=physical_interface, device=device_o, create_kwargs=attached_args, update_kwargs=attached_args)
            physical_interface_o.save()

    # Update the log
    log.ingested = True
    log.save()
