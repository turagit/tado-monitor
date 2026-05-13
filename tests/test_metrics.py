import unittest

from collector.tado_collector import metrics


class MetricsRenderingTest(unittest.TestCase):
    def test_renders_dashboard_compatible_metric_names_and_labels(self):
        snapshot = {
            "zones": [
                {
                    "name": "Office",
                    "type": "HEATING",
                    "setting_temperature": {"celsius": 21.0, "fahrenheit": 69.8},
                    "sensor_temperature": {"celsius": 22.25, "fahrenheit": 72.05},
                    "humidity": 45.6,
                    "heating_power": 0.0,
                    "ac_power": 1.0,
                    "window_open": False,
                }
            ],
            "weather": {
                "outside_temperature": {"celsius": 12.28, "fahrenheit": 54.1},
                "solar_intensity": 55.6,
            },
            "collector": {
                "last_success_timestamp": 1_700_000_000,
                "last_error": "",
                "auth_ok": True,
                "rate_limit_remaining": 99,
            },
        }

        rendered = metrics.render_metrics(snapshot)

        required = [
            'tado_activity_heating_power_percentage{type="HEATING",zone="Office"} 0',
            'tado_activity_ac_power_value{type="HEATING",zone="Office"} 1',
            'tado_setting_temperature_value{type="HEATING",unit="celsius",zone="Office"} 21',
            'tado_setting_temperature_value{type="HEATING",unit="fahrenheit",zone="Office"} 69.8',
            'tado_sensor_temperature_value{type="HEATING",unit="celsius",zone="Office"} 22.25',
            'tado_sensor_temperature_value{type="HEATING",unit="fahrenheit",zone="Office"} 72.05',
            'tado_sensor_humidity_percentage{type="HEATING",zone="Office"} 45.6',
            'tado_sensor_window_opened{type="HEATING",zone="Office"} 0',
            'weather_outside_temperature{unit="celsius"} 12.28',
            'weather_outside_temperature{unit="fahrenheit"} 54.1',
            "weather_solar_intensity 55.6",
            "tado_collector_last_success_timestamp_seconds 1700000000",
            "tado_collector_auth_ok 1",
            "tado_collector_rate_limit_remaining 99",
        ]
        for line in required:
            self.assertIn(line, rendered)

    def test_escapes_prometheus_label_values(self):
        snapshot = {
            "zones": [
                {
                    "name": 'Office "North"\\Wing',
                    "type": "HEATING",
                    "heating_power": 0.0,
                    "window_open": False,
                }
            ]
        }

        rendered = metrics.render_metrics(snapshot)

        self.assertIn('zone="Office \\"North\\"\\\\Wing"', rendered)


if __name__ == "__main__":
    unittest.main()
