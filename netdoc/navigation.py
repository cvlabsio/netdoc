from extras.plugins import PluginMenuButton, PluginMenuItem
from utilities.choices import ButtonColorChoices


credential_buttons = [
    PluginMenuButton(
        link='plugins:netdoc:credential_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN
    ),
    PluginMenuButton(
        link='plugins:netdoc:credential_import',
        title='Import',
        icon_class='mdi mdi-upload',
        color=ButtonColorChoices.CYAN
    )
]

discoverable_buttons = [
    PluginMenuButton(
        link='plugins:netdoc:discoverable_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN
    ),
    PluginMenuButton(
        link='plugins:netdoc:discoverable_import',
        title='Import',
        icon_class='mdi mdi-upload',
        color=ButtonColorChoices.CYAN
    )
]

menu_items = (
    PluginMenuItem(
        link="plugins:netdoc:credential_list",
        link_text="Credentials",
        buttons=credential_buttons
    ),
    PluginMenuItem(
        link='plugins:netdoc:discoverable_list',
        link_text='Discoverables',
        buttons=discoverable_buttons
    ),
    PluginMenuItem(
        link='plugins:netdoc:arptable_list',
        link_text='ARP Table',
    ),
    PluginMenuItem(
        link='plugins:netdoc:macaddresstable_list',
        link_text='MAC Address Table',
    ),
    PluginMenuItem(
        link='plugins:netdoc:routingtable_list',
        link_text='Routing Table',
    ),
    PluginMenuItem(
        link='plugins:netdoc:discoverylog_list',
        link_text='Logs',
    ),
)
