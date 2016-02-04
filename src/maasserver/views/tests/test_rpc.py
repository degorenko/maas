# Copyright 2014-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver RPC views."""

__all__ = []

import json
import os

from crochet import wait_for
from django.core.urlresolvers import reverse
from maasserver import eventloop
from maasserver.rpc.regionservice import RegionAdvertisingService
from maasserver.testing.eventloop import RegionEventLoopFixture
from maasserver.utils.threads import deferToDatabase
from maastesting.djangotestcase import DjangoTransactionTestCase
from netaddr import IPAddress
from provisioningserver.utils.network import get_all_interface_addresses
from testtools.matchers import (
    Equals,
    GreaterThan,
    IsInstance,
    KeysEqual,
    LessThan,
    MatchesAll,
    MatchesDict,
    MatchesListwise,
    MatchesSetwise,
)
from twisted.internet.defer import inlineCallbacks


is_valid_port = MatchesAll(
    IsInstance(int), GreaterThan(0), LessThan(2 ** 16))


class RPCViewTest(DjangoTransactionTestCase):

    def setUp(self):
        super(RPCViewTest, self).setUp()
        self.region_id_path = os.path.join(self.make_dir(), "region_id")
        self.patch(
            RegionAdvertisingService,
            "_get_path_to_region_id").return_value = self.region_id_path

    def test_rpc_info_when_rpc_advertise_not_present(self):
        getServiceNamed = self.patch_autospec(
            eventloop.services, "getServiceNamed")
        getServiceNamed.side_effect = KeyError

        response = self.client.get(reverse('rpc-info'))
        self.assertEqual("application/json", response["Content-Type"])
        info = json.loads(response.content.decode("unicode_escape"))
        self.assertEqual({"eventloops": None}, info)

    def test_rpc_info_when_rpc_advertise_not_running(self):
        response = self.client.get(reverse('rpc-info'))
        self.assertEqual("application/json", response["Content-Type"])
        info = json.loads(response.content.decode("unicode_escape"))
        self.assertEqual({"eventloops": None}, info)

    def test_rpc_info_when_rpc_advertise_running(self):
        self.useFixture(RegionEventLoopFixture("rpc", "rpc-advertise"))

        eventloop.start().wait(5)
        self.addCleanup(lambda: eventloop.reset().wait(5))

        getServiceNamed = eventloop.services.getServiceNamed

        @wait_for(5)
        @inlineCallbacks
        def wait_for_startup():
            # Wait for the rpc and the rpc-advertise services to start.
            yield getServiceNamed("rpc").starting
            yield getServiceNamed("rpc-advertise").starting
            # Force an update, because it's very hard to track when the
            # first iteration of the rpc-advertise service has completed.
            yield deferToDatabase(getServiceNamed("rpc-advertise").update)
        wait_for_startup()

        response = self.client.get(reverse('rpc-info'))

        self.assertEqual("application/json", response["Content-Type"])
        info = json.loads(response.content.decode("unicode_escape"))
        self.assertThat(info, KeysEqual("eventloops"))
        self.assertThat(info["eventloops"], MatchesDict({
            # Each entry in the endpoints dict is a mapping from an
            # event loop to a list of (host, port) tuples. Each tuple is
            # a potential endpoint for connecting into that event loop.
            eventloop.loop.name: MatchesSetwise(*(
                MatchesListwise((Equals(addr), is_valid_port))
                for addr in get_all_interface_addresses()
                if not IPAddress(addr).is_link_local() and
                IPAddress(addr).version == 4
            )),
        }))