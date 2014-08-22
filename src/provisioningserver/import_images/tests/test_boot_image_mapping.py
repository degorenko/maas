# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `BootImageMapping` and its module."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

import json

from maastesting.factory import factory
from maastesting.testcase import MAASTestCase
from provisioningserver.import_images.boot_image_mapping import (
    BootImageMapping,
    )
from provisioningserver.import_images.testing.factory import (
    make_image_spec,
    make_maas_meta,
    make_maas_meta_without_os,
    set_resource,
    )


class TestBootImageMapping(MAASTestCase):
    """Tests for `BootImageMapping`."""

    def test_initially_empty(self):
        self.assertItemsEqual([], BootImageMapping().items())

    def test_items_returns_items(self):
        image = make_image_spec()
        resource = factory.make_name('resource')
        image_dict = set_resource(image_spec=image, resource=resource)
        self.assertItemsEqual([(image, resource)], image_dict.items())

    def test_is_empty_returns_True_if_empty(self):
        self.assertTrue(BootImageMapping().is_empty())

    def test_is_empty_returns_False_if_not_empty(self):
        mapping = BootImageMapping()
        mapping.setdefault(make_image_spec(), factory.make_name('resource'))
        self.assertFalse(mapping.is_empty())

    def test_setdefault_sets_unset_item(self):
        image_dict = BootImageMapping()
        image = make_image_spec()
        resource = factory.make_name('resource')
        image_dict.setdefault(image, resource)
        self.assertItemsEqual([(image, resource)], image_dict.items())

    def test_setdefault_leaves_set_item_unchanged(self):
        image = make_image_spec()
        old_resource = factory.make_name('resource')
        image_dict = set_resource(image_spec=image, resource=old_resource)
        image_dict.setdefault(image, factory.make_name('newresource'))
        self.assertItemsEqual([(image, old_resource)], image_dict.items())

    def test_dump_json_is_consistent(self):
        image = make_image_spec()
        resource = factory.make_name('resource')
        image_dict_1 = set_resource(image_spec=image, resource=resource)
        image_dict_2 = set_resource(image_spec=image, resource=resource)
        self.assertEqual(image_dict_1.dump_json(), image_dict_2.dump_json())

    def test_dump_json_represents_empty_dict_as_empty_object(self):
        self.assertEqual('{}', BootImageMapping().dump_json())

    def test_dump_json_represents_entry(self):
        image = make_image_spec()
        resource = factory.make_name('resource')
        image_dict = set_resource(image_spec=image, resource=resource)
        self.assertEqual(
            {
                image.os: {
                    image.arch: {
                        image.subarch: {
                            image.release: {image.label: resource},
                        },
                    },
                },
            },
            json.loads(image_dict.dump_json()))

    def test_dump_json_combines_similar_entries(self):
        image = make_image_spec()
        other_release = factory.make_name('other-release')
        resource1 = factory.make_name('resource')
        resource2 = factory.make_name('other-resource')
        image_dict = BootImageMapping()
        set_resource(image_dict, image, resource1)
        set_resource(
            image_dict, image._replace(release=other_release), resource2)
        self.assertEqual(
            {
                image.os: {
                    image.arch: {
                        image.subarch: {
                            image.release: {image.label: resource1},
                            other_release: {image.label: resource2},
                        },
                    },
                },
            },
            json.loads(image_dict.dump_json()))

    def test_load_json_result_matches_dump_of_own_data(self):
        # Loading the test data and dumping it again should result in
        # identical test data.
        test_meta_file_content = make_maas_meta()
        mapping = BootImageMapping.load_json(test_meta_file_content)
        dumped = mapping.dump_json()
        self.assertEqual(test_meta_file_content, dumped)

    def test_load_json_result_of_old_data_uses_ubuntu_as_os(self):
        test_meta_file_content = make_maas_meta_without_os()
        mapping = BootImageMapping.load_json(test_meta_file_content)
        os = {image.os for image, _ in mapping.items()}.pop()
        self.assertEqual('ubuntu', os)

    def test_load_json_returns_empty_mapping_for_invalid_json(self):
        bad_json = ""
        mapping = BootImageMapping.load_json(bad_json)
        self.assertEqual({}, mapping.mapping)
