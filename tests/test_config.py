import unittest

from collector.tado_collector import config


class ConfigTest(unittest.TestCase):
    def test_defaults(self):
        cfg = config.load({})

        self.assertEqual(cfg.listen_address, "127.0.0.1:9898")
        self.assertEqual(cfg.token_file, "/var/lib/tado-history-dashboard/tokens/tado-token.json")
        self.assertEqual(cfg.poll_interval_seconds, 900)
        self.assertEqual(cfg.client_id, "1bb50063-6b0c-4d11-bd99-387f4a91cc46")
        self.assertEqual(cfg.tado_api_base_url, "https://my.tado.com")

    def test_environment_overrides(self):
        cfg = config.load(
            {
                "TADO_LISTEN_ADDRESS": "0.0.0.0:9999",
                "TADO_TOKEN_FILE": "/tmp/token.json",
                "TADO_POLL_INTERVAL": "30m",
                "TADO_CLIENT_ID": "client-2",
                "TADO_HOME_ID": "42",
                "TADO_API_BASE_URL": "https://example.test",
            }
        )

        self.assertEqual(cfg.listen_address, "0.0.0.0:9999")
        self.assertEqual(cfg.token_file, "/tmp/token.json")
        self.assertEqual(cfg.poll_interval_seconds, 1800)
        self.assertEqual(cfg.client_id, "client-2")
        self.assertEqual(cfg.home_id, 42)
        self.assertEqual(cfg.tado_api_base_url, "https://example.test")

    def test_duration_parser(self):
        self.assertEqual(config.parse_duration_seconds("45s"), 45)
        self.assertEqual(config.parse_duration_seconds("15m"), 900)
        self.assertEqual(config.parse_duration_seconds("2h"), 7200)
        self.assertEqual(config.parse_duration_seconds("900"), 900)


if __name__ == "__main__":
    unittest.main()
