from extras.plugins import PluginConfig
from django.conf import settings
import os

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get('netdoc', {})

class NetdocConfig(PluginConfig):
    name = 'netdoc'
    verbose_name = 'NetDoc'
    description = 'Automatic Network Documentation plugin for NetBox'
    version = '0.9.1'
    author = 'Andrea Dainese'
    author_email = 'andrea.dainese@pm.me'
    base_url = 'netdoc'
    required_settings = ['NTC_TEMPLATES_DIR']
    default_settings = {
        'NTC_TEMPLATES_DIR': '/opt/ntc-templates/ntc_templates/templates'
    }


config = NetdocConfig

# Setting NTC_TEMPLATES_DIR
os.environ.setdefault("NET_TEXTFSM", PLUGIN_SETTINGS.get('NTC_TEMPLATES_DIR'))
