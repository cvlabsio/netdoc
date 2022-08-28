from os.path import basename
import logging
import inspect
from slugify import slugify
from django.db.utils import IntegrityError
from . import functions

def ingest(log, force=False):
    """
    Processing show version.
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

    item = log.parsed_output[0] # Show version contains only one item

    # Parsing
    # https://github.com/networktocode/ntc-templates/tree/master/tests/cisco_ios/show_version
    name = item["hostname"]
    manufacturer = 'Cisco Systems'
    serial = next(iter(item["serial"]), None)
    site = log.discoverable.site
    create_argws = {
        'site': site,
        'manufacturer': manufacturer,
        'serial': serial,
    }
    update_argws = {
        'serial': serial,
    }

    # Trusted data: we always update some data
    device_o = functions.set_get_device(name=name, create_kwargs=create_argws, update_kwargs=update_argws)
    discoverable_o = functions.set_get_discoverable(address=log.discoverable.address, device=device_o, site=site, force=True)

    # Update the log
    log.ingested = True
    log.save()
