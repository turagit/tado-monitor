import unittest

from collector.tado_collector import tado


class TadoClientTest(unittest.TestCase):
    def test_collects_home_zones_states_and_weather(self):
        calls = []

        def request_json(url, access_token):
            calls.append(url)
            self.assertEqual(access_token, "access-token")
            if url.endswith("/api/v2/me"):
                return {"homes": [{"id": 42, "name": "Home"}]}, {"ratelimit": "limit=100, remaining=97, reset=3600"}
            if url.endswith("/api/v2/homes/42/zones"):
                return [{"id": 1, "name": "Office"}], {}
            if url.endswith("/api/v2/homes/42/zones/1/state"):
                return {
                    "setting": {
                        "deviceType": "HEATING",
                        "temperature": {"celsius": 21.0, "fahrenheit": 69.8},
                    },
                    "sensorDataPoints": {
                        "insideTemperature": {"celsius": 22.25, "fahrenheit": 72.05},
                        "humidity": {"percentage": 45.6},
                    },
                    "activityDataPoints": {
                        "heatingPower": {"percentage": 12.5},
                        "acPower": {"value": "OFF"},
                    },
                    "openWindow": None,
                }, {}
            if url.endswith("/api/v2/homes/42/weather"):
                return {
                    "solarIntensity": {"percentage": 55.6},
                    "outsideTemperature": {"celsius": 12.28, "fahrenheit": 54.1},
                }, {}
            raise AssertionError(f"unexpected URL {url}")

        client = tado.Client(base_url="https://my.tado.test", request_json=request_json)
        snapshot = client.collect("access-token")

        self.assertEqual(
            calls,
            [
                "https://my.tado.test/api/v2/me",
                "https://my.tado.test/api/v2/homes/42/zones",
                "https://my.tado.test/api/v2/homes/42/zones/1/state",
                "https://my.tado.test/api/v2/homes/42/weather",
            ],
        )
        self.assertEqual(snapshot["zones"][0]["name"], "Office")
        self.assertEqual(snapshot["zones"][0]["type"], "HEATING")
        self.assertEqual(snapshot["zones"][0]["heating_power"], 12.5)
        self.assertEqual(snapshot["zones"][0]["ac_power"], 0.0)
        self.assertFalse(snapshot["zones"][0]["window_open"])
        self.assertEqual(snapshot["weather"]["outside_temperature"]["celsius"], 12.28)
        self.assertEqual(snapshot["collector"]["rate_limit_remaining"], 97)

    def test_uses_configured_home_id_without_me_request(self):
        calls = []

        def request_json(url, _access_token):
            calls.append(url)
            if url.endswith("/api/v2/homes/7/zones"):
                return [], {}
            if url.endswith("/api/v2/homes/7/weather"):
                return {}, {}
            raise AssertionError(f"unexpected URL {url}")

        client = tado.Client(base_url="https://my.tado.test", request_json=request_json, home_id=7)
        client.collect("access-token")

        self.assertNotIn("https://my.tado.test/api/v2/me", calls)


if __name__ == "__main__":
    unittest.main()
