# NetDoc

A Network Documentation plugin for NetBox.

## Installing netbox

You should follow offical documentation, but just in case here is how I install netbox:

~~~
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential libxml2-dev libxslt1-dev libffi-dev libpq-dev libssl-dev zlib1g-dev
sudo useradd -M -U -d /opt/netbox netbox
sudo git clone --depth=1 https://github.com/netbox-community/netbox /opt/netbox
sudo chown netbox:netbox /opt/netbox/ -R
~~~

## Installing NetDoc prerequisites

~~~
sudo git clone --depth=1 https://github.com/networktocode/ntc-templates /opt/ntc-templates
sudo chown netbox:netbox /opt/ntc-templates -R
~~~

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
chmod 600 /opt/netbox/netbox/netbox/configuration.py
~~~

Edit the configuration file as following:

~~~
ALLOWED_HOSTS = ['*']
DATABASE = {
    'NAME': 'netbox',
    'USER': 'netbox',
    'PASSWORD': '0123456789abcdef',
    'HOST': 'localhost',
    'PORT': '',
    'CONN_MAX_AGE': 300,
}
DEVELOPER = True
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
PLUGINS = ['netbox_netdoc']
SECRET_KEY = '01234567890123456789012345678901234567890123456789'
~~~

Upgrade and install dependeincies for netbox:

~~~
sudo -u netbox /opt/netbox/upgrade.sh
~~~

## Starting netbox

Under `/opt/netbox/contrib/` you can find startup scripts for both netbox and scheduler (`netbox-rq`).

~~~
sudo cp -v /opt/netbox/contrib/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable netbox netbox-rq
sudo systemctl start netbox netbox-rq
~~~

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
