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
        # https://github.com/networktocode/ntc-templates/tree/master/tests/cisco_nxos/show_vlan
        site_o = log.discoverable.device.site
        vlan_id = item["vlan_id"]
        vlan_name = item["name"]
        vlan_status = item["status"]

        # Trusted data: we always update some data
        vlan_o = functions.set_get_vlan(vid=vlan_id, name=vlan_name, site=site_o)

    # Update the log
    log.discoverable.save()
    log.ingested = True
    log.save()
