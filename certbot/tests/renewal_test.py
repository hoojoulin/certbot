"""Tests for certbot._internal.renewal"""
import unittest

try:
    import mock
except ImportError:  # pragma: no cover
    from unittest import mock

from acme import challenges
from certbot import errors
from certbot._internal import configuration
from certbot._internal import storage
import certbot.tests.util as test_util


class RenewalTest(test_util.ConfigTestCase):
    @mock.patch('certbot._internal.cli.set_by_cli')
    def test_ancient_webroot_renewal_conf(self, mock_set_by_cli):
        mock_set_by_cli.return_value = False
        rc_path = test_util.make_lineage(
            self.config.config_dir, 'sample-renewal-ancient.conf')
        self.config.account = None
        self.config.email = None
        self.config.webroot_path = None
        config = configuration.NamespaceConfig(self.config)
        lineage = storage.RenewableCert(rc_path, config)
        renewalparams = lineage.configuration['renewalparams']
        # pylint: disable=protected-access
        from certbot._internal import renewal
        renewal._restore_webroot_config(config, renewalparams)
        self.assertEqual(config.webroot_path, ['/var/www/'])

    @mock.patch('certbot._internal.renewal.cli.set_by_cli')
    def test_webroot_params_conservation(self, mock_set_by_cli):
        # For more details about why this test is important, see:
        # certbot._internal.plugins.webroot_test::
        #   WebrootActionTest::test_webroot_map_partial_without_perform
        from certbot._internal import renewal
        mock_set_by_cli.return_value = False

        renewalparams = {
            'webroot_map': {'test.example.com': '/var/www/test'},
            'webroot_path': ['/var/www/test', '/var/www/other'],
        }
        renewal._restore_webroot_config(self.config, renewalparams)  # pylint: disable=protected-access
        self.assertEqual(self.config.webroot_map, {'test.example.com': '/var/www/test'})
        self.assertEqual(self.config.webroot_path, ['/var/www/test', '/var/www/other'])

        renewalparams = {
            'webroot_map': {},
            'webroot_path': '/var/www/test',
        }
        renewal._restore_webroot_config(self.config, renewalparams)  # pylint: disable=protected-access
        self.assertEqual(self.config.webroot_map, {})
        self.assertEqual(self.config.webroot_path, ['/var/www/test'])

    def test_reuse_key_renewal_params(self):
        self.config.rsa_key_size = 'INVALID_VALUE'
        self.config.reuse_key = True
        self.config.dry_run = True
        config = configuration.NamespaceConfig(self.config)

        rc_path = test_util.make_lineage(
            self.config.config_dir, 'sample-renewal.conf')
        lineage = storage.RenewableCert(rc_path, config)

        le_client = mock.MagicMock()
        le_client.obtain_certificate.return_value = (None, None, None, None)

        from certbot._internal import renewal

        with mock.patch('certbot._internal.renewal.hooks.renew_hook'):
            renewal.renew_cert(self.config, None, le_client, lineage)

        assert self.config.rsa_key_size == 2048

    def test_reuse_ec_key_renewal_params(self):
        self.config.elliptic_curve = 'INVALID_CURVE'
        self.config.reuse_key = True
        self.config.dry_run = True
        self.config.key_type = 'ecdsa'
        config = configuration.NamespaceConfig(self.config)

        rc_path = test_util.make_lineage(
            self.config.config_dir,
            'sample-renewal-ec.conf',
            ec=True,
        )
        lineage = storage.RenewableCert(rc_path, config)

        le_client = mock.MagicMock()
        le_client.obtain_certificate.return_value = (None, None, None, None)

        from certbot._internal import renewal

        with mock.patch('certbot._internal.renewal.hooks.renew_hook'):
            renewal.renew_cert(self.config, None, le_client, lineage)

        assert self.config.elliptic_curve == 'secp256r1'


class RestoreRequiredConfigElementsTest(test_util.ConfigTestCase):
    """Tests for certbot._internal.renewal.restore_required_config_elements."""
    @classmethod
    def _call(cls, *args, **kwargs):
        from certbot._internal.renewal import restore_required_config_elements
        return restore_required_config_elements(*args, **kwargs)

    @mock.patch('certbot._internal.renewal.cli.set_by_cli')
    def test_allow_subset_of_names_success(self, mock_set_by_cli):
        mock_set_by_cli.return_value = False
        self._call(self.config, {'allow_subset_of_names': 'True'})
        self.assertTrue(self.config.allow_subset_of_names is True)

    @mock.patch('certbot._internal.renewal.cli.set_by_cli')
    def test_allow_subset_of_names_failure(self, mock_set_by_cli):
        mock_set_by_cli.return_value = False
        renewalparams = {'allow_subset_of_names': 'maybe'}
        self.assertRaises(
            errors.Error, self._call, self.config, renewalparams)

    @mock.patch('certbot._internal.renewal.cli.set_by_cli')
    def test_pref_challs_list(self, mock_set_by_cli):
        mock_set_by_cli.return_value = False
        renewalparams = {'pref_challs': 'http-01, dns'.split(',')}
        self._call(self.config, renewalparams)
        expected = [challenges.HTTP01.typ, challenges.DNS01.typ]
        self.assertEqual(self.config.pref_challs, expected)

    @mock.patch('certbot._internal.renewal.cli.set_by_cli')
    def test_pref_challs_str(self, mock_set_by_cli):
        mock_set_by_cli.return_value = False
        renewalparams = {'pref_challs': 'dns'}
        self._call(self.config, renewalparams)
        expected = [challenges.DNS01.typ]
        self.assertEqual(self.config.pref_challs, expected)

    @mock.patch('certbot._internal.renewal.cli.set_by_cli')
    def test_pref_challs_failure(self, mock_set_by_cli):
        mock_set_by_cli.return_value = False
        renewalparams = {'pref_challs': 'finding-a-shrubbery'}
        self.assertRaises(errors.Error, self._call, self.config, renewalparams)

    @mock.patch('certbot._internal.renewal.cli.set_by_cli')
    def test_must_staple_success(self, mock_set_by_cli):
        mock_set_by_cli.return_value = False
        self._call(self.config, {'must_staple': 'True'})
        self.assertTrue(self.config.must_staple is True)

    @mock.patch('certbot._internal.renewal.cli.set_by_cli')
    def test_must_staple_failure(self, mock_set_by_cli):
        mock_set_by_cli.return_value = False
        renewalparams = {'must_staple': 'maybe'}
        self.assertRaises(
            errors.Error, self._call, self.config, renewalparams)

    @mock.patch('certbot._internal.renewal.cli.set_by_cli')
    def test_ancient_server_renewal_conf(self, mock_set_by_cli):
        from certbot._internal import constants
        self.config.server = None
        mock_set_by_cli.return_value = False
        self._call(self.config, {'server': constants.V1_URI})
        self.assertEqual(self.config.server, constants.CLI_DEFAULTS['server'])


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
