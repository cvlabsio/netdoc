import re
import os
import importlib
from netmiko.utilities import get_structured_data
from netdoc.models import DiscoveryLog
from netdoc.ingestors.functions import log_ingest


INVALID_RE = [
    # WARNING: must specify ^/$ or a very unique string not found in valid outputs
    r"^$", # Empty result
    r"^\^", # Cisco Error (e.g. "^Note: ")
    r"^% ", # Generic Cisco error (e.g. "% Invalid command")
    r"^\s*\^\n%", # Cisco Error (e.g. "^\n% Invalid...")
    r"^No spanning tree instances exist", # Cisco
    # r"% Invalid input detected", # Cisco (with ^ the % is not at the beginning)
    # r"% Invalid command at", # Cisco (with ^ the % is not at the beginning)
    r"% \w* is not enabled$", # Cisco XR put datetime before the error
    r"% \w* not active$", # Cisco XR put datetime before the error
]


CONFIG_CMD = [
    r"running-config",
]


class ModeNotDetected(Exception):
    pass


class FailedToParse(Exception):
    pass


def is_config(cmd):
    for regex in CONFIG_CMD:
        # Check if the command expects a configuration
        if re.search(regex, cmd):
            return True
    return False


def log_create(discoverable=None, raw_output=None, request=None, **kwargs):
    """
    Create a log.
    """
    log = None

    kwargs['success'] = valid_output(raw_output)
    kwargs['configuration'] = is_config(request)

    # Extract command from request if they differ (e.g. 'show ip arp|show ip arp vrf x')
    kwargs['command'] = request.split('|').pop()
    request = request.split('|').pop(0)

    log = DiscoveryLog.objects.create(discoverable=discoverable, raw_output=raw_output, request=request, **kwargs)

    # Try to parse
    try:
        log = log_parse(log)
    except:
        pass

    # Try to ingest
    try:
        log = log_ingest(log)
    except:
        pass

    return log


def log_parse(log):
    parsed = False
    parsed_output = None
    try:
        framework = log.discoverable.mode.split('_').pop(0)
        platform = '_'.join(log.discoverable.mode.split('_')[1:])
    except:
        raise ModeNotDetected
    if framework == 'netmiko':
        parsed_output = parse_netmiko_output(log.raw_output, platform=platform, command=log.request)
        parsed = True
    else:
        raise ModeNotDetected

    log.parsed = parsed
    log.parsed_output = parsed_output
    log.save()
    return log


def parse_netmiko_output(output, command=None, platform=None):
    try:
        parsed_output = get_structured_data(output, platform=platform, command=command)
        if not isinstance(parsed_output, dict) and not isinstance(parsed_output, list):
            raise FailedToParse
    except Exception:
        raise FailedToParse
    return parsed_output


def valid_output(output):
    for regex in INVALID_RE:
        # Check if the output is valid
        if re.search(regex, output):
            return False
    return True
