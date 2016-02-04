# Copyright 2014-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""RPC declarations for clusters.

These are commands that a cluster controller ought to respond to.
"""

__all__ = [
    "Authenticate",
    "ConfigureDHCPv4",
    "ConfigureDHCPv6",
    "DescribePowerTypes",
    "GetPreseedData",
    "Identify",
    "ListBootImages",
    "ListOperatingSystems",
    "ListSupportedArchitectures",
    "PowerOff",
    "PowerOn",
    "PowerQuery",
    "PowerDriverCheck",
    "ValidateLicenseKey",
]

from provisioningserver.power.poweraction import (
    PowerActionFail,
    UnknownPowerType,
)
from provisioningserver.rpc import exceptions
from provisioningserver.rpc.arguments import (
    AmpList,
    Bytes,
    CompressedAmpList,
    ParsedURL,
    StructureAsJSON,
)
from provisioningserver.rpc.common import (
    Authenticate,
    Identify,
)
from provisioningserver.twisted.protocols import amp


class ListBootImages(amp.Command):
    """List the boot images available on this cluster controller.

    :since: 1.5
    """

    arguments = []
    response = [
        (b"images", AmpList(
            [(b"osystem", amp.Unicode()),
             (b"architecture", amp.Unicode()),
             (b"subarchitecture", amp.Unicode()),
             (b"release", amp.Unicode()),
             (b"label", amp.Unicode()),
             (b"purpose", amp.Unicode()),
             (b"xinstall_type", amp.Unicode()),
             (b"xinstall_path", amp.Unicode())]))
    ]
    errors = []


class ListBootImagesV2(amp.Command):
    """List the boot images available on this cluster controller.

    This command compresses the images list to allow more images in the
    response and to remove the amp.TooLong error.

    :since: 1.7.6
    """

    arguments = []
    response = [
        (b"images", CompressedAmpList(
            [(b"osystem", amp.Unicode()),
             (b"architecture", amp.Unicode()),
             (b"subarchitecture", amp.Unicode()),
             (b"release", amp.Unicode()),
             (b"label", amp.Unicode()),
             (b"purpose", amp.Unicode()),
             (b"xinstall_type", amp.Unicode()),
             (b"xinstall_path", amp.Unicode())]))
    ]
    errors = []


class DescribePowerTypes(amp.Command):
    """Get a JSON Schema describing this cluster's power types.

    :since: 1.5
    """

    arguments = []
    response = [
        (b"power_types", StructureAsJSON()),
    ]
    errors = []


class ListSupportedArchitectures(amp.Command):
    """Report the cluster's supported architectures.

    :since: 1.5
    """

    arguments = []
    response = [
        (b"architectures", AmpList([
            (b"name", amp.Unicode()),
            (b"description", amp.Unicode()),
            ])),
    ]
    errors = []


class ListOperatingSystems(amp.Command):
    """Report the cluster's supported operating systems.

    :since: 1.7
    """

    arguments = []
    response = [
        (b"osystems", AmpList([
            (b"name", amp.Unicode()),
            (b"title", amp.Unicode()),
            (b"releases", AmpList([
                (b"name", amp.Unicode()),
                (b"title", amp.Unicode()),
                (b"requires_license_key", amp.Boolean()),
                (b"can_commission", amp.Boolean()),
            ])),
            (b"default_release", amp.Unicode(optional=True)),
            (b"default_commissioning_release", amp.Unicode(optional=True)),
        ])),
    ]
    errors = []


class GetOSReleaseTitle(amp.Command):
    """Get the title for the operating systems release.

    :since: 1.7
    """

    arguments = [
        (b"osystem", amp.Unicode()),
        (b"release", amp.Unicode()),
    ]
    response = [
        (b"title", amp.Unicode()),
    ]
    errors = {
        exceptions.NoSuchOperatingSystem: (
            b"NoSuchOperatingSystem"),
    }


class ValidateLicenseKey(amp.Command):
    """Validate an OS license key.

    :since: 1.7
    """

    arguments = [
        (b"osystem", amp.Unicode()),
        (b"release", amp.Unicode()),
        (b"key", amp.Unicode()),
    ]
    response = [
        (b"is_valid", amp.Boolean()),
    ]
    errors = {
        exceptions.NoSuchOperatingSystem: (
            b"NoSuchOperatingSystem"),
    }


class PowerDriverCheck(amp.Command):
    """Check power driver on cluster for missing packages

    :since: 1.9
    """

    arguments = [
        (b"power_type", amp.Unicode()),
    ]
    response = [
        (b"missing_packages", amp.ListOf(amp.Unicode())),
    ]
    errors = {
        UnknownPowerType: (
            b"UnknownPowerType"),
        NotImplementedError: (
            b"NotImplementedError"),
    }


class GetPreseedData(amp.Command):
    """Get OS-specific preseed data.

    :since: 1.7
    """

    arguments = [
        (b"osystem", amp.Unicode()),
        (b"preseed_type", amp.Unicode()),
        (b"node_system_id", amp.Unicode()),
        (b"node_hostname", amp.Unicode()),
        (b"consumer_key", amp.Unicode()),
        (b"token_key", amp.Unicode()),
        (b"token_secret", amp.Unicode()),
        (b"metadata_url", ParsedURL()),
    ]
    response = [
        (b"data", StructureAsJSON()),
    ]
    errors = {
        exceptions.NoSuchOperatingSystem: (
            b"NoSuchOperatingSystem"),
        NotImplementedError: (
            b"NotImplementedError"),
    }


class _Power(amp.Command):
    """Base class for power control commands.

    :since: 1.7
    """

    arguments = [
        (b"system_id", amp.Unicode()),
        (b"hostname", amp.Unicode()),
        (b"power_type", amp.Unicode()),
        # We can't define a tighter schema here because this is a highly
        # variable bag of arguments from a variety of sources.
        (b"context", StructureAsJSON()),
    ]
    response = []
    errors = {
        UnknownPowerType: (
            b"UnknownPowerType"),
        NotImplementedError: (
            b"NotImplementedError"),
        PowerActionFail: (
            b"PowerActionFail"),
        exceptions.PowerActionAlreadyInProgress: (
            b"PowerActionAlreadyInProgress"),
    }


class PowerOn(_Power):
    """Turn a node's power on.

    :since: 1.7
    """


class PowerOff(_Power):
    """Turn a node's power off.

    :since: 1.7
    """


class PowerQuery(_Power):
    """Query a node's power state.

    :since: 1.7
    """
    response = [
        (b"state", amp.Unicode()),
    ]


class _ConfigureDHCP(amp.Command):
    """Configure a DHCP server.

    :since: 1.7
    """
    arguments = [
        (b"omapi_key", amp.Unicode()),
        (b"subnet_configs", AmpList([
            (b"subnet", amp.Unicode()),
            (b"subnet_mask", amp.Unicode()),
            (b"subnet_cidr", amp.Unicode()),
            (b"broadcast_ip", amp.Unicode()),
            (b"interface", amp.Unicode()),
            (b"router_ip", amp.Unicode()),
            (b"dns_servers", amp.Unicode()),
            (b"ntp_server", amp.Unicode()),
            (b"domain_name", amp.Unicode()),
            (b"ip_range_low", amp.Unicode()),
            (b"ip_range_high", amp.Unicode()),
            (b"hosts", CompressedAmpList([
                ("host", amp.Unicode()),
                ("mac", amp.Unicode()),
                ("ip", amp.Unicode()),
                ], optional=True))
            ])),
        ]
    response = []
    errors = {exceptions.CannotConfigureDHCP: b"CannotConfigureDHCP"}


class ConfigureDHCPv4(_ConfigureDHCP):
    """Configure the DHCPv4 server.

    :since: 1.7
    """


class ConfigureDHCPv6(_ConfigureDHCP):
    """Configure the DHCPv6 server.

    :since: 1.7
    """


class RemoveHostMaps(amp.Command):
    """Remove host maps from the DHCP server's configuration.

    :since: 1.7
    """

    arguments = [
        (b"ip_addresses", amp.ListOf(amp.Unicode())),
        (b"shared_key", amp.Unicode()),
    ]
    response = []
    errors = {
        exceptions.CannotRemoveHostMap: (
            b"CannotRemoveHostMap"),
    }


class ImportBootImages(amp.Command):
    """Import boot images and report the final
    boot images that exist on the cluster.

    :since: 1.7
    """

    arguments = [
        (b"sources", AmpList(
            [(b"url", amp.Unicode()),
             (b"keyring_data", Bytes()),
             (b"selections", AmpList(
                 [(b"os", amp.Unicode()),
                  (b"release", amp.Unicode()),
                  (b"arches", amp.ListOf(amp.Unicode())),
                  (b"subarches", amp.ListOf(amp.Unicode())),
                  (b"labels", amp.ListOf(amp.Unicode()))]))])),
        (b"http_proxy", ParsedURL(optional=True)),
        (b"https_proxy", ParsedURL(optional=True)),
    ]
    response = []
    errors = []


class EvaluateTag(amp.Command):
    """Evaluate a tag against the list of nodes.

    :since: 2.0
    """

    arguments = [
        (b"tag_name", amp.Unicode()),
        (b"tag_definition", amp.Unicode()),
        (b"tag_nsmap", AmpList([
            (b"prefix", amp.Unicode()),
            (b"uri", amp.Unicode()),
        ])),
        # A 3-part credential string for the web API.
        (b"credentials", amp.Unicode()),
        # List of nodes the rack controller should evaluate.
        (b"nodes", AmpList([
            (b"system_id", amp.Unicode()),
        ])),
    ]
    response = []
    errors = []


class AddVirsh(amp.Command):
    """Probe for and enlist virsh VMs attached to the cluster.

    :since: 1.7
    """

    arguments = [
        (b"user", amp.Unicode()),
        (b"poweraddr", amp.Unicode()),
        (b"password", amp.Unicode(optional=True)),
        (b"prefix_filter", amp.Unicode(optional=True)),
        (b"accept_all", amp.Boolean(optional=True)),
    ]
    response = []
    errors = []


class AddSeaMicro15k(amp.Command):
    """Probe for and enlist seamicro15k machines attached to the cluster.

    :since: 1.7
    """
    arguments = [
        (b"user", amp.Unicode()),
        (b"mac", amp.Unicode()),
        (b"username", amp.Unicode()),
        (b"password", amp.Unicode()),
        (b"power_control", amp.Unicode(optional=True)),
        (b"accept_all", amp.Boolean(optional=True)),
    ]
    response = []
    errors = {
        exceptions.NoIPFoundForMACAddress: b"NoIPFoundForMACAddress",
    }


class AddVMware(amp.Command):
    """Probe for and enlist VMware virtual machines.

    :since: 1.8
    """
    arguments = [
        (b"user", amp.Unicode()),
        (b"host", amp.Unicode()),
        (b"username", amp.Unicode()),
        (b"password", amp.Unicode()),
        (b"port", amp.Integer(optional=True)),
        (b"protocol", amp.Unicode(optional=True)),
        (b"prefix_filter", amp.Unicode(optional=True)),
        (b"accept_all", amp.Boolean(optional=True)),
    ]
    response = []
    errors = {}


class EnlistNodesFromMSCM(amp.Command):
    """Probe for and enlist mscm machines attached to the cluster.

    :since: 1.7
    """
    arguments = [
        (b"user", amp.Unicode()),
        (b"host", amp.Unicode()),
        (b"username", amp.Unicode()),
        (b"password", amp.Unicode()),
        (b"accept_all", amp.Boolean(optional=True)),
    ]
    response = []
    errors = {}


class EnlistNodesFromUCSM(amp.Command):
    """Probe for and enlist ucsm machines attached to the cluster.

    :since: 1.7
    """
    arguments = [
        (b"user", amp.Unicode()),
        (b"url", amp.Unicode()),
        (b"username", amp.Unicode()),
        (b"password", amp.Unicode()),
        (b"accept_all", amp.Boolean(optional=True)),
    ]
    response = []
    errors = {}


class EnlistNodesFromMicrosoftOCS(amp.Command):
    """Probe for and enlist msftocs machines attached to the cluster.

    :since: 1.8
    """
    arguments = [
        (b"user", amp.Unicode()),
        (b"ip", amp.Unicode()),
        (b"port", amp.Unicode()),
        (b"username", amp.Unicode()),
        (b"password", amp.Unicode()),
        (b"accept_all", amp.Boolean(optional=True)),
    ]
    response = []
    errors = {}


class IsImportBootImagesRunning(amp.Command):
    """Check if the import boot images task is running on the cluster.

    :since: 1.7
    """
    arguments = []
    response = [
        (b"running", amp.Boolean()),
    ]
    errors = {}


class RefreshRackControllerInfo(amp.Command):
    """Refresh the rack controller's hardware and network details.

    :since: 2.0
    """
    arguments = [
        (b"system_id", amp.Unicode()),
        (b"consumer_key", amp.Unicode()),
        (b"token_key", amp.Unicode()),
        (b"token_secret", amp.Unicode()),
    ]
    response = [
        (b"architecture", amp.Unicode()),
        (b"osystem", amp.Unicode()),
        (b"distro_series", amp.Unicode()),
        (b"swap_size", amp.Integer()),
    ]
    errors = {}