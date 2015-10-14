# Copyright 2014-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the ``maasregiond`` TAP."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

import crochet
from maasserver import eventloop
from maasserver.plugin import (
    MAX_THREADS,
    Options,
    RegionServiceMaker,
)
from maastesting.matchers import MockCalledOnceWith
from maastesting.testcase import MAASTestCase
from provisioningserver import logger
from provisioningserver.utils.twisted import asynchronous
from testtools.matchers import GreaterThan
from twisted.application.service import MultiService
from twisted.internet import reactor


class TestOptions(MAASTestCase):
    """Tests for `maasserver.plugin.Options`."""

    def test_defaults(self):
        options = Options()
        self.assertEqual({"introspect": None}, options.defaults)

    def test_parse_minimal_options(self):
        options = Options()
        # The minimal set of options that must be provided.
        arguments = []
        options.parseOptions(arguments)  # No error.


class TestRegionServiceMaker(MAASTestCase):
    """Tests for `maasserver.plugin.RegionServiceMaker`."""

    def setUp(self):
        super(TestRegionServiceMaker, self).setUp()
        self.patch(eventloop.loop, "services", MultiService())
        self.patch_autospec(crochet, "no_setup")

    def test_init(self):
        service_maker = RegionServiceMaker("Harry", "Hill")
        self.assertEqual("Harry", service_maker.tapname)
        self.assertEqual("Hill", service_maker.description)

    @asynchronous(timeout=5)
    def test_makeService(self):
        """
        Only the site service is created when no options are given.
        """
        self.patch_autospec(logger, "basicConfig")
        options = Options()
        service_maker = RegionServiceMaker("Harry", "Hill")
        service = service_maker.makeService(options)
        self.assertIsInstance(service, MultiService)
        expected_services = [
            "import-resources",
            "import-resources-progress",
            "nonce-cleanup",
            "rpc",
            "rpc-advertise",
            "web",
        ]
        self.assertItemsEqual(expected_services, service.namedServices)
        self.assertEqual(
            len(service.namedServices), len(service.services),
            "Not all services are named.")
        self.assertThat(logger.basicConfig, MockCalledOnceWith())
        self.assertThat(crochet.no_setup, MockCalledOnceWith())

    @asynchronous(timeout=5)
    def test__sets_pool_size(self):
        service_maker = RegionServiceMaker("Harry", "Hill")
        service_maker.makeService(Options())
        threadpool = reactor.getThreadPool()
        self.assertEqual(MAX_THREADS, threadpool.max)
        # Max threads is reasonable.
        self.assertThat(threadpool.max, GreaterThan(50))