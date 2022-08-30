# NetDoc

NetDoc is an automatic network documentation plugin for NetBox. NetDoc aims to discover a partially known network populating netbox and drawing L2 and L3 diagrams.

NetDoc:

* Discovers, via nornir+netmiko, network devices fetching information (routing, adjacencies, configuration...).
* Populate netbox (devices, cables, IPAM).

Network diagrams are currently provided by netbox-topology-views plugin. See [my blog post](https://www.adainese.it/blog/2022/08/28/netdoc-automated-network-discovery-and-documentation/ "NetDoc: automated network discovery and documentation") for more information.

## Installing netbox

You should follow the offical documentation, but just in case here is how I install netbox:

~~~
sudo apt install -y apache2 python3 python3-pip python3-venv python3-dev build-essential libxml2-dev libxslt1-dev libffi-dev libpq-dev libssl-dev zlib1g-dev
sudo useradd -M -U -d /opt/netbox netbox
sudo git clone --depth=1 https://github.com/netbox-community/netbox /opt/netbox
sudo chown netbox:netbox /opt/netbox/ -R
~~~

## Installing NetDoc prerequisites

~~~
sudo git clone --depth=1 https://github.com/networktocode/ntc-templates /opt/ntc-templates
sudo chown netbox:netbox /opt/ntc-templates -R
~~~

NetDoc must be included in netbox plugins and configured in the main netbox configuration file (see below).

## Creating the netbox database

~~~
sudo -u postgres psql
create database netbox;
create user netbox with password '0123456789abcdef';
grant all privileges on database netbox to netbox;
~~~

## Configuring netbox

You should follow offical documentation, but just in case here is how I configure netbox:

~~~
sudo -u netbox cp -a /opt/netbox/netbox/netbox/configuration_example.py /opt/netbox/netbox/netbox/configuration.py
sudo -u netbox cp /opt/netbox/contrib/gunicorn.py /opt/netbox/gunicorn.py
sudo -u netbox chmod 600 /opt/netbox/netbox/netbox/configuration.py
sudo openssl req -x509 -newkey rsa:4096 -keyout /etc/ssl/private/netbox.key -nodes -out /etc/ssl/certs/netbox.crt -sha256 -days 3650
sudo cp /opt/netbox/contrib/apache.conf /etc/apache2/sites-available/001-netbox.conf
sudo a2enmod proxy ssl headers proxy_http
sudo a2ensite 001-netbox
sudo find /opt/netbox/netbox/static/ -type f -exec chmod a+r {} \;
sudo find /opt/netbox/ -type d -exec chmod a+xr {} \;
~~~

Edit the configuration file (`configuration.py`) as following:

~~~
ALLOWED_HOSTS = ['*']
DEVELOPER = True
DATABASE = {
    'NAME': 'netbox',
    'USER': 'netbox',
    'PASSWORD': '0123456789abcdef',
    'HOST': 'localhost',
    'PORT': '',
    'CONN_MAX_AGE': 300,
}
REDIS = {
    'tasks': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 0,
        'SSL': False,
    },
    'caching': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 1,
        'SSL': False,
    }
}
PLUGINS = ['netdoc', 'netbox_topology_views']
PLUGINS_CONFIG = {
    'netdoc': {
        'NTC_TEMPLATES_DIR': '/opt/ntc-templates/ntc_templates/templates'
    },
    'netbox_topology_views': {
        'allow_coordinates_saving': True,
        'draw_default_layout': True,
        'draw_interface_name': True,
    }
}
SECRET_KEY = '01234567890123456789012345678901234567890123456789'
~~~

Upgrade and install dependencies for netbox:

~~~
sudo -u netbox echo netdoc >> /opt/netbox/local_requirements.txt
sudo -u netbox echo netbox-topology-views >> /opt/netbox/local_requirements.txt
sudo -u netbox /opt/netbox/upgrade.sh
~~~

Create first administrative user:

~~~
sudo -u netbox /opt/netbox/venv/bin/python3 /opt/netbox/netbox/manage.py createsuperuser
~~~

## Starting netbox

Under `/opt/netbox/contrib/` you can find startup scripts for both netbox and scheduler (`netbox-rq`).

~~~
sudo cp -v /opt/netbox/contrib/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable netbox netbox-rq apache2
sudo systemctl start netbox netbox-rq apache2
~~~

Netbox is listening by default on localhost:8001 (see `/opt/netbox/contrib/gunicorn.py`). Apache is serving as a reverse proxy.

## Developing NetDoc

Install NetDoc as a development module:

~~~
mkdir ~/src
git clone https://github.com/dainok/netdoc ~/src/netdoc
~~~

Starting netbox:

~~~
cd ~/src/netdoc
/opt/netbox/venv/bin/python3 setup.py develop
/opt/netbox/venv/bin/python3 manage.py runserver 0.0.0.0:8000 --insecure
/opt/netbox/venv/bin/python3 manage.py rqworker high default low
~~~

## Debugging

Discover script:

~~~
from netdoc import tasks

tasks.discovery(["172.25.82.34","172.25.82.39","172.25.82.40"])
~~~

Parsers:

~~~
from netdoc import models
import importlib
from netdoc import functions
import logging
import pprint

request = "show vrf"
mode = "netmiko_cisco_nxos"
request = "show ip interface"
mode = None

logs = models.DiscoveryLog.objects.all()

request = "show vrf"
mode = "netmiko_cisco_nxos"
request = "show ip interface"
mode = None

if mode:
        logs = logs.filter(discoverable__mode=mode)
if request:
        logs = logs.filter(request=request)
logs = logs.filter(success=True)

for log in logs:
    functions.log_parse(log)
    pprint.pprint(log.parsed_output)
    print('Parsed:', log.parsed)
    print('Items:', len(log.parsed_output))
~~~

Ingest scripts:

~~~
from netdoc import models
import importlib
from netdoc.ingestors import functions
import logging

request = "show vrf"
mode = "netmiko_cisco_nxos"
request = "show ip interface"
mode = None

logs = models.DiscoveryLog.objects.all()
if mode:
        logs = logs.filter(discoverable__mode=mode)
if request:
        logs = logs.filter(request=request)
logs = logs.filter(parsed=True)

for log in logs:
        try:
                functions.log_ingest(log)
        except functions.NoIngestor:
                pass
        except functions.Postponed as err:
                print(err)
~~~

## References

* [PostgreSQL Database Installation](https://docs.netbox.dev/en/stable/installation/1-postgresql/ "PostgreSQL Database Installation")
* [Redis Installation](https://docs.netbox.dev/en/stable/installation/2-redis/ "Redis Installation")
* [NetBox Installation](https://docs.netbox.dev/en/stable/installation/3-netbox/ "NetBox Installation")
* [Gunicorn](https://docs.netbox.dev/en/stable/installation/4-gunicorn/ "Gunicorn")
* [HTTP Server Setup](https://docs.netbox.dev/en/stable/installation/5-http-server/ "HTTP Server Setup")
