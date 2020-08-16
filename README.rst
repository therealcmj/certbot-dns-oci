certbot-dns-oci
===============

Oracle Cloud Infrastructure (OCI) DNS Authenticator plugin for Certbot.

This plugin automates the process of completing a ``dns-01`` challenge by
creating, and subsequently removing, TXT records using OCI's DNS API.

Configuration:
--------------

Install and configure the OCI CLI. See https://docs.cloud.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm
for details.

To use this authenticator you will need:

* a registered domain name, configured with the OCI DNS servers
* that domain name created in OCI (via the console, the CLI, or the API)
* an OCI account with adequate permission to Create / Update / Delete DNS entries in that domain

Installation
------------

I haven't published this in PyPI yet. So for the time being you need to install from source.

::

    git clone git@github.com:therealcmj/certbot-dns-oci.git
    cd certbot-dns-oci
    pip install .


or

::

    git clone git@github.com:therealcmj/certbot-dns-oci.git
    pip install ./certbot-dns-oci


Development
-----------

If you want to work on the code you should create a virtual environment and install it there:

::

    git clone git@github.com:therealcmj/certbot-dns-oci.git
    cd certbot-dns-oci
    virtualenv dev
    . ./dev/bin/activate
    pip install -e .

You can then use your IDE as normal on the live code.

To use the debugger be sure to choose the correct virtual environment. For PyCharm go to Debug, Edit Configurations
and then update the Interpreter to point to the newly created Virtual Environment.

Arguments
---------

This plug-in supports the following arguments on certbot's command line:

======================================= ========================================================
``--authenticator dns-oci``             Select the OCI DNS authenticator plugin (Required)

``--dns-oci-config``                    OCI configuration file.
                                        If ommitted the default configuration file will be used.
                                        (Optional)

``--dns-oci-profile``                   Specify an alternative profile in the OCI
                                        configuration file.
                                        If omitted the DEFAULT profile will be used.
                                        (Optional)

``--dns-oci-propagation-seconds``       Amount of time to allow for the DNS change to propagate
                                        before asking the ACME server to verify the DNS record.
                                        (Default: 15)
======================================= ========================================================


Examples
--------

To acquire a TEST certificate for demosite.ociateam.com:

.. code-block:: bash

    certbot --test-cert certonly \
     --logs-dir logs --work-dir work --config-dir config \
     --authenticator dns-oci -d demosite.ociateam.com


To acquire a *real* certificate for demosite.ociateam.com:

.. code-block:: bash

    certbot certonly \
     --logs-dir logs --work-dir work --config-dir config \
     --authenticator dns-oci -d demosite.ociateam.com

