from os.path import basename
import logging
import inspect
from slugify import slugify
from . import functions

def ingest(log, force=False):
    """
    Processing show vrf.
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

    for item in log.parsed_output:
        # Parsing
        # https://github.com/networktocode/ntc-templates/tree/master/tests/cisco_ios/show_vrf
        vrf_name = item["name"]
        vrf_rd = item["default_rd"]
        create_kwargs={'rd': vrf_rd}
        update_kwargs={'rd': vrf_rd}

        # Trusted data: we always update some data
        vrf_o = functions.set_get_vrf(name=vrf_name, create_kwargs=create_kwargs, update_kwargs=update_kwargs)

    # Update the log
    log.discoverable.save()
    log.ingested = True
    log.save()
