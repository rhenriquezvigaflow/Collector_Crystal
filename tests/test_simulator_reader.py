from __future__ import annotations

import unittest

from workers.get_simulator import SimulatedTagReader


class SimulatedTagReaderTests(unittest.TestCase):
    def test_reader_generates_values_from_yaml_like_specs(self) -> None:
        reader = SimulatedTagReader(
            {
                "PH": {"type": "float", "min": 7.0, "max": 8.0, "decimals": 2},
                "STATE": {"type": "state", "values": [0, 1]},
                "MODE": {"type": "choice", "values": ["AUTO", "MANUAL"]},
            },
            seed=1,
        )

        values = reader.read_once()

        self.assertGreaterEqual(values["PH"], 7.0)
        self.assertLessEqual(values["PH"], 8.0)
        self.assertIn(values["STATE"], [0, 1])
        self.assertIn(values["MODE"], ["AUTO", "MANUAL"])

if __name__ == "__main__":
    unittest.main()
