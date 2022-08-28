import json
from ctypes import addressof
from django.utils import timezone
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result
from nornir.core.filter import F
from . import models
from . import functions


def discovery(nr=None):
    """
    Discovery Cisco XR devices
    """
    mode = "netmiko"
    platform = "cisco_xr"
    filtered_devices = nr.filter(platform=platform)
    logs = []

    # Define tasks
    def multiple_tasks(task):
        """
        Define tasks for the playbook. CMD line is passed also as name, so we
        can log cmdline, stdout (result) and parsed output.
        """
        task.run(
            task=netmiko_send_command,
            name="show running-config",
            command_string="show running-config",
            use_textfsm=False,
        )
        task.run(task=netmiko_send_command, name="show version", command_string="show version", use_textfsm=False)
        task.run(task=netmiko_send_command, name="show logging", command_string="show logging", use_textfsm=False)
        task.run(
            task=netmiko_send_command, name="show interfaces", command_string="show interfaces", use_textfsm=False
        )
        task.run(
            task=netmiko_send_command,
            name="show cdp neighbors detail",
            command_string="show cdp neighbors detail",
            use_textfsm=False,
        )
        task.run(
            task=netmiko_send_command,
            name="show lldp neighbors detail",
            command_string="show lldp neighbors detail",
            use_textfsm=False,
        )
        task.run(task=netmiko_send_command, name="show vrf", command_string="show vrf all", use_textfsm=False)
        task.run(
            task=netmiko_send_command, name="show ipv4 interface", command_string="show ipv4 interface", use_textfsm=False
        )
        task.run(
            task=netmiko_send_command, name="show hsrp", command_string="show hsrp", use_textfsm=False
        )
        task.run(
            task=netmiko_send_command, name="show vrrp", command_string="show vrrp", use_textfsm=False
        )
        task.run(
            task=netmiko_send_command, name="show ospf neighbor", command_string="show ospf neighbor", use_textfsm=False
        )
        task.run(
            task=netmiko_send_command, name="show eigrp neighbors", command_string="show eigrp neighbors", use_textfsm=False
        )
        task.run(
            task=netmiko_send_command, name="show bgp neighbors", command_string="show bgp neighbors", use_textfsm=False
        )

    # Run the playbook
    aggregated_results = filtered_devices.run(task=multiple_tasks)

    # Print the result
    print_result(aggregated_results)

    for key, multi_result in aggregated_results.items():
        vrfs = ["default"] # Adding default VRF
        current_nr = nr.filter(F(name=key))

        # MultiResult is an array of Result
        for result in multi_result:
            if result.name == "multiple_tasks":
                # Skip MultipleTask
                continue

            address = result.host.dict()["hostname"]
            discoverable = models.Discoverable.objects.get(address=address, mode=f'{mode}_{platform}')
            discoverable.last_discovered_at = timezone.now() # Update last_discovered_at
            discoverable.save()

            # Log locally
            log = functions.log_create(
                discoverable=discoverable,
                raw_output=result.result,
                request=result.name,
            )
            
            # Save log for later
            logs.append(log)

            # Save VRF list for later
            if result.name == "show vrf":
                try:
                    vrf_parsed_output = functions.parse_netmiko_output(result.result, platform=platform, command=result.name)
                except:
                    vrf_parsed_output = []
                for entry in vrf_parsed_output:
                    vrfs.append(entry["name"])

        # Additional commands out of the multi result loop
        def additional_tasks(task):
            """
            Define additional tasks for the playbook.
            """
            # Per VRF commands
            for vrf in vrfs:
                if vrf == "default":
                    # Default VRF has no name
                    task.run(task=netmiko_send_command, name="show arp", command_string="show arp", use_textfsm=False)
                    task.run(task=netmiko_send_command, name="show route", command_string="show route", use_textfsm=False)
                else:
                    task.run(task=netmiko_send_command, name=f'show arp|show arp vrf {vrf}', command_string=f'show ip arp vrf {vrf}', use_textfsm=False)
                    task.run(task=netmiko_send_command, name=f'show route|show route vrf {vrf}', command_string=f'show ip route vrf {vrf}', use_textfsm=False)

        # Run the additional playbook
        additional_aggregated_results = current_nr.run(task=additional_tasks)

        # Print the result
        print_result(additional_aggregated_results)

        for key, additional_multi_result in additional_aggregated_results.items():
            # MultiResult is an array of Result
            for result in additional_multi_result:
                if result.name == "additional_tasks":
                    # Skip MultipleTask
                    continue

                # Log locally
                log = functions.log_create(
                    discoverable=discoverable,
                    raw_output=result.result,
                    request=result.name,
                )

                # Save log for later
                logs.append(log)
