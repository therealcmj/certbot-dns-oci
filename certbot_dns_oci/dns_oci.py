"""DNS Authenticator for OCI."""
import logging

from certbot import errors
from certbot import interfaces
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
        # self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):  # pylint: disable=arguments-differ
        super(Authenticator, cls).add_parser_arguments(
            add, default_propagation_seconds=60
        )
        # TODO: implement these:
        add('config', help="OCI CLI Configuration file.")
        add('profile', help="OCI configuration profile (in OCI configuration file)")
        # Add argument for instance principal
        add('instance-principal',help="Use instance principal for authentication.")

    def validate_options(self):
        # Validate options to ensure that conflicting arguments are not provided together
        if self.conf('instance-principal') and self.conf('config'):
            raise errors.PluginError(
                "Conflicting arguments: '--dns-oci-instance-principal' and '--dns-oci-config' cannot be provided together."
            )

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return (
            "This plugin configures a DNS TXT record to respond to a dns-01 challenge using "
            + "the OCI REST API."
        )

    def _setup_credentials(self):
        # Validate options
        self.validate_options()
        
        oci_config_profile = 'DEFAULT'
        if self.conf('profile') is not None:
                oci_config_profile = self.conf('profile')
                self.credentials = oci.config.from_file(profile_name=oci_config_profile)


    def _perform(self, domain, validation_name, validation):
        self._get_ocidns_client().add_txt_record(
            domain, validation_name, validation, self.ttl
        )

    def _cleanup(self, domain, validation_name, validation):
        self._get_ocidns_client().del_txt_record(
            domain, validation_name, validation
        )

    def _get_ocidns_client(self):
        if self.conf('instance-principal') is not None:
            return _OCIDNSClient()
        else:
            return _OCIDNSClient(self.credentials)


class _OCIDNSClient:
    """
    This class handles calling OCI SDK / REST API needed for this use case.
    This is a FAR from complete implementation of anything and is really
    only intended for my own use.
    In Other Words: thar be dragons
    """

    def __init__(self, oci):
        logger.debug("creating OCI DnsClient Using Config File")
        # this is where you would add code to handle Resource, Instance, or non-default configs
        config = oci.config.from_file()
        self.dns_client = oci.dns.DnsClient(oci.ci_config)

    def __init__(self):
        logger.debug("creating OCI DnsClient Using Instance Principal")
        # this is where you would add code to handle Resource, Instance, or non-default configs
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        self.dns_client = oci.dns.DnsClient(config={}, signer=signer)

    def add_txt_record(self, domain, record_name, record_content, record_ttl):
        """
        Add a TXT record using the supplied information.

        :param str domain: The domain to use to look up the OCI DNS zone.
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content (typically the challenge validation).
        :param int record_ttl: The record TTL (number of seconds that the record may be cached).
        :raises certbot.errors.PluginError: if an error occurs communicating with the OCI API
        """

        # check to see if the DNS zone is present in OCI

        # first find the domain
        zone_ocid, zone_name = self._find_managed_zone(domain, record_name)
        if zone_name is None:
            raise errors.PluginError("Domain not known. Please Make sure the domain is in OCI DNS and You have the correct permissions.")
        logger.debug("Found domain %s with OCID %s", zone_name, zone_ocid)

        # NOTE: the OCI SDK will treat:
        #  - an addition of the same name + value + TTL as a NO OP
        #  - an addition of the same name + value (but different TTL) as an update to the TTL
        # it does NOT throw an error in either case.

        logger.debug("Setting record %s in zone %s to value %s w/ TTL %d",
                     record_name, zone_ocid, record_content, record_ttl)

        result = self.dns_client.patch_domain_records(
            zone_name,
            record_name,
            oci.dns.models.PatchDomainRecordsDetails( items=[ oci.dns.models.RecordOperation(
                operation='ADD',
                domain=record_name,
                ttl=record_ttl,
                rtype='TXT',
                rdata=record_content) ] ) )

        logger.debug("Update successful.")
        logger.debug("New rrset version: %s", result.data.items[0].rrset_version)

        logger.debug("Success")

    # note: add_txt_record takes a 4th parameter for the ttl
    #       but ALL records with the same name have the same TTL
    #       so just in case anyone else changed the TTL on us unexpectedly
    #       we just delete the record with the name, type (TXT), and value we created
    def del_txt_record(self, domain, record_name, record_content):
        """
        Delete a TXT record using the supplied information.

        :param str domain: The domain name
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content

        :raises certbot.errors.PluginError: if the domain name is not known
        """
        # first find the domain
        zone_ocid, zone_name = self._find_managed_zone(domain, record_name)
        if zone_name is None:
            raise errors.PluginError("Domain not known")
        logger.debug("Found domain %s with OCID %s", zone_name, zone_ocid)

        result = self.dns_client.patch_domain_records(
            zone_name,
            record_name,
            oci.dns.models.PatchDomainRecordsDetails( items=[ oci.dns.models.RecordOperation(
                operation='REMOVE',
                domain=record_name,
                rtype='TXT',
                rdata=record_content
            ) ] ) )

        logger.debug("Success")

    def _find_managed_zone(self, domain, record_name):
        """
        Find the managed zone for a given domain.

        :param str domain: The domain for which to find the managed zone.
        :returns: The ID of the managed zone, if found.
        :rtype: str
        :raises certbot.errors.PluginError: if the managed zone cannot be found.
        """

        zone_dns_name_guesses = [record_name] + dns_common.base_domain_name_guesses(domain)

        logger.debug("Guesses: ")
        for zone_name in zone_dns_name_guesses:
            logger.debug(" - %s", zone_name)

        for zone_name in zone_dns_name_guesses:
            # get the zone id
            try:
                logger.debug("looking for zone: %s", zone_name)
                try:
                    response = self.dns_client.get_zone(zone_name)
                    if response.status == 200:
                        logger.debug("Response data %s", response.data)
                        logger.debug("Found zone: %s", zone_name)
                        logger.debug("OCID: %s", response.data.id)
                        logger.debug("Compartment: %s", response.data.compartment_id)
                        return response.data.id, zone_name
                except oci.exceptions.ServiceError as e:
                    logger.debug("Zone '%s' not found", zone_name)
            except errors.PluginError as e:
                pass
        return None, None
