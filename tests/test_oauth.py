import os
import stat
import tempfile
import time
import unittest

from collector.tado_collector import oauth


class OAuthTokenTest(unittest.TestCase):
    def test_save_and_load_token_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "tokens", "tado.json")
            token = oauth.Token("access", "refresh", int(time.time()) + 3600)

            oauth.save_token(path, token)
            loaded = oauth.load_token(path)

            self.assertEqual(loaded.access_token, "access")
            self.assertEqual(loaded.refresh_token, "refresh")
            self.assertTrue(loaded.is_valid())
            mode = stat.S_IMODE(os.stat(path).st_mode)
            self.assertEqual(mode, 0o600)

    def test_refresh_token_request_shape(self):
        seen = {}

        def post_form(_url, params):
            seen.update(params)
            return {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 120,
            }

        token = oauth.Token("old-access", "old-refresh", int(time.time()) - 1)
        refreshed = oauth.refresh_token(token, "client-1", "https://example.test/token", post_form=post_form)

        self.assertEqual(seen["grant_type"], "refresh_token")
        self.assertEqual(seen["client_id"], "client-1")
        self.assertEqual(seen["refresh_token"], "old-refresh")
        self.assertEqual(refreshed.access_token, "new-access")
        self.assertEqual(refreshed.refresh_token, "new-refresh")
        self.assertGreater(refreshed.expires_at, int(time.time()))

    def test_start_device_auth_and_poll_until_success(self):
        calls = []

        def post_form(_url, params):
            calls.append(params.get("grant_type", "device"))
            if params.get("grant_type") == "urn:ietf:params:oauth:grant-type:device_code":
                if len(calls) == 2:
                    raise oauth.OAuthPending()
                return {
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 600,
                }
            return {
                "device_code": "device-123",
                "user_code": "ABCD-EFGH",
                "verification_uri": "https://login.tado.com/activate",
                "verification_uri_complete": "https://login.tado.com/activate?user_code=ABCD-EFGH",
                "expires_in": 600,
                "interval": 1,
            }

        challenge = oauth.start_device_auth("client-1", "https://example.test/device", post_form=post_form)
        token = oauth.poll_device_token(
            challenge,
            "client-1",
            "https://example.test/token",
            sleep=lambda _: None,
            now=lambda: int(time.time()),
            post_form=post_form,
        )

        self.assertEqual(challenge.device_code, "device-123")
        self.assertEqual(token.access_token, "access")
        self.assertIn("urn:ietf:params:oauth:grant-type:device_code", calls)


if __name__ == "__main__":
    unittest.main()
