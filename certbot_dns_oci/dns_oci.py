"""DNS Authenticator for OCI."""
import logging

from certbot import errors
from certbot.plugins import dns_common

import oci

logger = logging.getLogger(__name__)


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for Oracle Cloud Infrastructure DNS service

    This Authenticator uses the OCI REST API to fulfill a dns-01 challenge.
    """

    description = "Obtain certificates using a DNS TXT record (if you are using OCI for DNS)."
    ttl = 60

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)

    @classmethod
    def add_parser_arguments(cls, add, **kwargs):
        super(Authenticator, cls).add_parser_arguments(
            add, default_propagation_seconds=15
        )
        add('oci-config', help="OCI CLI Configuration file.")
        add('oci-profile', help="OCI configuration profile (in OCI configuration file)")
        add('oci-instance-principal', help="Use instance principal for authentication.")

    def validate_options(self):
        # Validate options to ensure that conflicting arguments are not provided together
        if self.conf('oci-instance-principal') and self.conf('oci-config'):
            raise errors.PluginError(
                "Conflicting arguments: 'oci-instance-principal' and 'oci-config' cannot be provided together."
            )

    def _setup_credentials(self):
        if self.conf('oci-instance-principal'):
            self.credentials = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        else:
            oci_config_profile = 'DEFAULT'
            if self.conf('oci-profile') is not None:
                oci_config_profile = self.conf('oci-profile')
            self.credentials = oci.config.from_file(profile_name=oci_config_profile)

    def more_info(self):
        return (
            "This plugin configures a DNS TXT record to respond to a dns-01 challenge using "
            + "the OCI REST API."
        )

    def _perform(self, domain, validation_name, validation):
        self._get_ocidns_client().add_txt_record(
            domain, validation_name, validation, self.ttl
        )

    def _cleanup(self, domain, validation_name, validation):
        self._get_ocidns_client().del_txt_record(
            domain, validation_name, validation
        )

    def _get_ocidns_client(self):
        return _OCIDNSClient(self.credentials)


class _OCIDNSClient:
    """
    This class handles calling OCI SDK / REST API needed for this use case.
    """

    def __init__(self, oci_config):
        logger.debug("creating OCI DnsClient")
        self.dns_client = oci.dns.DnsClient(oci_config)

    def add_txt_record(self, domain, record_name, record_content, record_ttl):
        # Implementation for adding TXT record

    def del_txt_record(self, domain, record_name, record_content):
        # Implementation for deleting TXT record
