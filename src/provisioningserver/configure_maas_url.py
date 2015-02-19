# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Management command: update `MAAS_URL`.

The MAAS cluster controller packaging calls this in order to set a new
"MAAS URL" (the URL where nodes and cluster controllers can reach the
region controller) in the cluster controller's configuration files.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'add_arguments',
    'run',
    ]

from urlparse import urlparse
from provisioningserver import __init__


CLUSTERD_DB_PATH = '/var/lib/maas/clusterd.db'
CLUSTERD_DB_maas_url = 'MAAS_URL'
CLUSTERD_DB_generator = 'generator'
CLUSTERD_DB_cluster_uuid = 'CLUSTER_UUID'


def replace_host(new_host, line):
    url = urlparse(line)
    url = url._replace(netloc="%s:%i"%(new_host,url.port))
    return url.geturl()


def update_maas_cluster_conf(host):
    """Update `MAAS_URL`
    """
    from maascli.config import ProfileConfig
    with ProfileConfig.open(CLUSTERD_DB_PATH) as config:
        urlbefore = config[CLUSTERD_DB_maas_url]
        urlafter = replace_host(host, urlbefore)
        config[CLUSTERD_DB_maas_url] = urlafter


def update_generator_url(host):
    """The generator line must look something like::

        http://10.9.8.7/MAAS/api/1.0/pxeconfig/

    The host part of the URL (in this example, `10.9.8.7`) will be replaced
    with the new `host`.  If `host` is an IPv6 address, this function will
    ensure that it is surrounded by square brackets.
    """

    from maascli.config import ProfileConfig
    with ProfileConfig.open(CLUSTERD_DB_PATH) as config:
        urlbefore = config[CLUSTERD_DB_generator]
        urlafter = replace_host(host, urlbefore)
        config[CLUSTERD_DB_generator] = urlafter


def add_arguments(parser):
    """Add this command's options to the `ArgumentParser`.

    Specified by the `ActionScript` interface.
    """
    parser.add_argument(
        'maas_url', metavar='URL',
        help=(
            "URL where nodes and cluster controllers can reach the MAAS "
            "region controller."))


def run(args):
    """Update MAAS_URL setting in configuration files.

    For use by the MAAS packaging scripts.  Updates configuration files
    to reflect a new MAAS_URL setting.
    """
    update_maas_cluster_conf(urlparse(args.maas_url).netloc)
    update_generator_url(urlparse(args.maas_url).netloc)
