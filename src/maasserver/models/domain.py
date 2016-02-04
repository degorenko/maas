# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Domain objects."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    "DEFAULT_DOMAIN_NAME",
    "dns_kms_setting_changed",
    "Domain",
    "NAME_VALIDATOR",
    "NAMESPEC",
    "validate_domain_name",
    ]

import datetime
import re

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.core.validators import RegexValidator
from django.db.models import (
    Manager,
    NullBooleanField,
    PositiveIntegerField,
    Q,
)
from django.db.models.query import QuerySet
from maasserver import DefaultMeta
from maasserver.fields import DomainNameField
from maasserver.models.cleansave import CleanSave
from maasserver.models.config import Config
from maasserver.models.timestampedmodel import TimestampedModel
from maasserver.utils.orm import MAASQueriesMixin

# Labels are at most 63 octets long, and a name can be many of them.
LABEL = r'[a-zA-Z0-9]([-a-zA-Z0-9]{0,62}[a-zA-Z0-9]){0,1}'
NAMESPEC = r'(%s.)*%s.?' % (LABEL, LABEL)


def validate_domain_name(value):
    """Django validator: `value` must be a valid DNS Zone name."""
    namespec = re.compile("^%s$" % NAMESPEC)
    if not namespec.search(value) or len(value) > 255:
        raise ValidationError("Invalid domain name: %s." % value)

NAME_VALIDATOR = RegexValidator("^%s$" % NAMESPEC)

# Name of the special, default domain.  This domain cannot be deleted.
DEFAULT_DOMAIN_NAME = 'maas'


def dns_kms_setting_changed():
    """Config.windows_kms_host has changed.

    Update any 'SRV 0 0 1688 ' DNSResource records for _vlmcs._tcp in
    ALL domains.
    """
    kms_host = Config.objects.get_config('windows_kms_host')
    for domain in Domain.objects.filter(authoritative=True):
        domain.update_kms_srv(kms_host)


class DomainQueriesMixin(MAASQueriesMixin):

    def get_specifiers_q(self, specifiers, separator=':', **kwargs):
        # This dict is used by the constraints code to identify objects
        # with particular properties. Please note that changing the keys here
        # can impact backward compatibility, so use caution.
        specifier_types = {
            None: self._add_default_query,
            'name': "__name",
            'id': "__id",
        }
        return super(DomainQueriesMixin, self).get_specifiers_q(
            specifiers, specifier_types=specifier_types, separator=separator,
            **kwargs)


class DomainQuerySet(QuerySet, DomainQueriesMixin):
    """Custom QuerySet which mixes in some additional queries specific to
    this object. This needs to be a mixin because an identical method is needed
    on both the Manager and all QuerySets which result from calling the
    manager.
    """


class DomainManager(Manager, DomainQueriesMixin):
    """Manager for :class:`Domain` model."""

    def get_queryset(self):
        queryset = DomainQuerySet(self.model, using=self._db)
        return queryset

    def get_default_domain(self):
        """Return the default domain."""
        now = datetime.datetime.now()
        domain, created = self.get_or_create(
            id=0,
            defaults={
                'id': 0,
                'name': DEFAULT_DOMAIN_NAME,
                'authoritative': True,
                'ttl': None,
                'created': now,
                'updated': now,
            }
        )
        return domain

    def get_domain_or_404(self, specifiers, user, perm):
        """Fetch a `Domain` by its id.  Raise exceptions if no `Domain` with
        this id exist or if the provided user has not the required permission
        to access this `Domain`.

        :param specifiers: The domain specifiers.
        :type specifiers: string
        :param user: The user that should be used in the permission check.
        :type user: django.contrib.auth.models.User
        :param perm: The permission to assert that the user has on the node.
        :type perm: unicode
        :raises: django.http.Http404_,
            :class:`maasserver.exceptions.PermissionDenied`.

        .. _django.http.Http404: https://
           docs.djangoproject.com/en/dev/topics/http/views/
           #the-http404-exception
        """
        domain = self.get_object_by_specifiers_or_raise(specifiers)
        if user.has_perm(perm, domain):
            return domain
        else:
            raise PermissionDenied()


class Domain(CleanSave, TimestampedModel):
    """A `Domain`.

    :ivar name: The DNS stuffix for this zone
    :ivar authoritative: MAAS manages this (forward) DNS zone.
    :ivar objects: An instance of the class :class:`DomainManager`.
    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""
        verbose_name = "Domain"
        verbose_name_plural = "Domains"

    objects = DomainManager()

    name = DomainNameField(
        max_length=256, editable=True, null=False, blank=False, unique=True,
        validators=[validate_domain_name])

    # We manage the forward zone.
    authoritative = NullBooleanField(
        default=True, db_index=True, editable=True)

    # Default TTL for this Domain.
    # If None and not overridden lower, then we will use the global default.
    ttl = PositiveIntegerField(default=None, null=True, blank=True)

    def update_kms_srv(self, kms_host=-1):
        # avoid recursive imports
        from maasserver.models import (
            DNSData,
            DNSResource,
        )
        # Since None and '' are both valid values, we use -1 as the "I want the
        # default value" indicator, and fetch the Config value accordingly.
        if kms_host == -1:
            kms_host = Config.objects.get_config('windows_kms_host')
        if kms_host is None or kms_host == '':
            # No more Config.windows_kms_host, so we need to delete the kms
            # host entries that we may have created.  The for loop is over 0 or
            # 1 DNSResource records
            for dnsrr in self.dnsresource_set.filter(name='_vlmcs._tcp'):
                dnsrr.dnsdata_set.filter(
                    rrtype='SRV',
                    rrdata__startswith='0 0 1688 '
                    ).delete()
        else:
            # force kms_host to be an FQDN (with trailing dot.)
            validate_domain_name(kms_host)
            if not kms_host.endswith('.'):
                kms_host += '.'
            # The windows_kms_host config parameter only manages priority 0,
            # weight 0, port 1688.  To do something different, use the
            # dnsresources api.
            srv_data = "0 0 1688 %s" % (kms_host)
            dnsrr, _ = DNSResource.objects.get_or_create(
                domain_id=self.id, name='_vlmcs._tcp', defaults={})
            srv, created = DNSData.objects.update_or_create(
                dnsresource_id=dnsrr.id, rrtype='SRV',
                rrdata__startswith="0 0 1688 ",
                defaults=dict(rrdata=srv_data))

    def get_base_ttl(self, rrtype, default_ttl):
        # If there is a Resource Record set, which has a non-None TTL, then it
        # wins.  Otherwise our ttl if we have one, or the passed-in default.
        from maasserver.models import DNSData
        rrset = DNSData.objects.filter(
            rrtype=rrtype, ttl__isnull=False).filter(
            Q(dnsresource__name='@') | Q(dnsresource__name='')).filter(
            dnsresource__domain_id=self.id)
        if rrset.count() > 0:
            return rrset.first().ttl
        elif self.ttl is not None:
            return self.ttl
        else:
            return default_ttl

    @property
    def resource_count(self):
        """How many DNSResource names are attached to this domain."""
        from maasserver.models.dnsresource import DNSResource
        return DNSResource.objects.filter(domain_id=self.id).count()

    @property
    def resource_record_count(self):
        """How many total Resource Records come from non-Nodes."""
        from maasserver.models.dnsdata import DNSData
        from maasserver.models.staticipaddress import StaticIPAddress
        ip_count = StaticIPAddress.objects.filter(
            dnsresource__domain_id=self.id).count()
        rr_count = DNSData.objects.filter(
            dnsresource__domain_id=self.id).count()
        return ip_count + rr_count

    def __str__(self):
        return "name=%s" % self.get_name()

    def __unicode__(self):
        return "name=%s" % self.get_name()

    def is_default(self):
        """Is this the default domain?"""
        return self.id == 0

    def get_name(self):
        """Return the name of the domain."""
        return self.name

    def delete(self):
        if self.is_default():
            raise ValidationError(
                "This domain is the default domain, it cannot be deleted.")
        super(Domain, self).delete()

    def save(self, *args, **kwargs):
        created = self.id is None
        super(Domain, self).save(*args, **kwargs)
        if created:
            self.update_kms_srv()

    def clean_name(self):
        # Automatically strip any trailing dot from the domain name.
        if self.name is not None and self.name.endswith('.'):
            self.name = self.name[:-1]

    def clean(self, *args, **kwargs):
        super(Domain, self).clean(*args, **kwargs)
        self.clean_name()

    def render_json_for_related_ips(self):
        """Render a representation of this domain's related IP addresses,
        suitable for converting to JSON."""
        from maasserver.models import StaticIPAddress
        # Get all of the address mappings.
        ip_mapping = StaticIPAddress.objects.get_hostname_ip_mapping(self)
        domainname_len = len(self.name)
        data = [
            {
                # strip off the domain name.
                'hostname': hostname[:-domainname_len - 1],
                'system_id': info.system_id,
                'ttl': info.ttl,
                'ips': info.ips,
            }
            for hostname, info in ip_mapping.items()
        ]
        return sorted(data, key=lambda json: json['hostname'])

    def render_json_for_related_rrdata(self):
        """Render a representation of this domain's related non-IP data,
        suitable for converting to JSON."""
        from maasserver.models import DNSData
        rr_mapping = DNSData.objects.get_hostname_dnsdata_mapping(self)
        data = [
            {
                'hostname': hostname,
                'system_id': info.system_id,
                'rrsets': info.rrset,
            }
            for hostname, info in rr_mapping.items()
        ]
        return sorted(data, key=lambda json: json['hostname'])