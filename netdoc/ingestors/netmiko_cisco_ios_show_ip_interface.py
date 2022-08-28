from os.path import basename
import logging
import inspect
from slugify import slugify
import ipaddress
from . import functions

def ingest(log, force=False):
    """
    Processing show ip interface.
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
        # https://github.com/networktocode/ntc-templates/tree/master/tests/cisco_ios/show_ip_interface
        device_o = log.discoverable.device
        interface_name = item['intf']
        vrf_name = item['vrf']
        vrf_o = functions.set_get_vrf(name=vrf_name, create_kwargs={})
        site_o = device_o.site
        create_args = {
            'name': interface_name,
        }

        if vrf_name:
            vrf_o = functions.set_get_vrf(name=vrf_name, create_kwargs={})
            update_args = {'vrf': vrf_o}
        else:
            update_args = {'vrf': None}

        # Trusted data: we always update some data
        interface_o = functions.set_get_interface(label=interface_name, device=device_o, create_kwargs=create_args, update_kwargs=update_args)

        # List all IP addresses
        addresses = []
        addresses_text = []
        for index, ipaddr in enumerate(item["ipaddr"]):
            addresses.append(ipaddress.IPv4Interface(f'{ipaddr}/{item["mask"][index]}'))
            addresses_text.append(str(ipaddress.IPv4Interface(f'{ipaddr}/{item["mask"][index]}')))

        # Removing removed addresses
        for configured_ip_address_o in interface_o.ip_addresses.all():
            if force and str(configured_ip_address_o.address) not in addresses_text:
                # Configured IP address not present in output
                interface_o.ip_addresses.remove(configured_ip_address_o)

        # Create IP addresses and prefixes
        for address in addresses:
            # Skip if IP address is present even with a different IPAddress.vrf
            if interface_o.ip_addresses.filter(address=str(address.with_prefixlen)):
                continue

            # Trusted data: we always update some data
            ip_address_o = functions.set_get_ip_address(address=str(address.with_prefixlen), create_kwargs={'vrf': vrf_o}, update_kwargs={'vrf': vrf_o})
            prefix_o = functions.set_get_prefix(prefix=str(address.network), create_kwargs={'vrf': vrf_o, 'site': site_o})

            # Add IP address to the interface
            try:
                # IP address already present
                interface_o.ip_addresses.get(pk=ip_address_o.pk)
            except:
                # Adding IP address
                interface_o.ip_addresses.add(ip_address_o)
                interface_o.save()

            if str(address.ip) == log.discoverable.address:
                # Set managament IP address
                device_o.primary_ip4 = ip_address_o
                device_o.save()

    # Update the log
    log.ingested = True
    log.save()
