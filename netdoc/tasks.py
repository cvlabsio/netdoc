import logging
import django_rq
import pprint

from nornir.core.plugins.inventory import InventoryPluginRegister
from .nornir_inventory import AssetInventory
from nornir import InitNornir
from nornir.core.filter import F
from . import discovery_cisco_ios, discovery_cisco_nxos, discovery_cisco_xr


def discovery(addresses):
    # Configuring Nornir
    logger = logging.getLogger("nornir")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler("nornir.log")
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    # Load Nornir custom inventory
    InventoryPluginRegister.register("asset-inventory", AssetInventory)

    # Create Nornir inventory
    nr = InitNornir(
        runner={
            "plugin": "threaded",
            "options": {
                "num_workers": 100,
            },
        },
        inventory={"plugin": "asset-inventory"},
        logging={"enabled": False},
    )

    # Execute on a selected hosts only
    # See https://theworldsgonemad.net/2021/nornir-inventory/
    nr = nr.filter(F(hostname__in=addresses))

    # Starting discovery job
    pprint.pprint(nr.dict())
    discovery_cisco_ios.discovery(nr)
    discovery_cisco_nxos.discovery(nr)
    discovery_cisco_xr.discovery(nr)
