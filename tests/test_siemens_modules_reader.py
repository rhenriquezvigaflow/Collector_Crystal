import unittest

from workers.get_siemens import SiemensModulesReader


class _FakeReader:
    def __init__(self, **kwargs) -> None:
        self.tag_map = kwargs["tag_map"]

    def read_once(self) -> dict:
        return {
            tag_id: index
            for index, tag_id in enumerate(self.tag_map, start=1)
        }


class _FailingReader:
    def __init__(self, **_kwargs) -> None:
        pass

    def read_once(self) -> dict:
        raise ConnectionError("offline")


class SiemensModulesReaderTests(unittest.TestCase):
    def test_merges_modules_and_supplemental_tags(self) -> None:
        reader = SiemensModulesReader(
            [
                {
                    "id": "pump_a",
                    "driver": "siemens",
                    "opc_server_url": "opc.tcp://10.0.0.10:4840",
                    "tags": {
                        "STATE_A": "ns=4;i=1",
                        "VALUE_A": "ns=4;i=2",
                    },
                }
            ],
            supplemental_tags={"TEMP": 28.4},
            reader_factory=_FakeReader,
        )

        self.assertEqual(
            reader.read_once(),
            {
                "TEMP": 28.4,
                "STATE_A": 1,
                "VALUE_A": 2,
            },
        )

    def test_preserves_supplemental_tags_when_module_is_offline(self) -> None:
        reader = SiemensModulesReader(
            [
                {
                    "id": "pump_a",
                    "driver": "siemens",
                    "ip": "10.0.0.10",
                    "tags": {"STATE_A": "ns=4;i=1"},
                }
            ],
            supplemental_tags={"TEMP": 28.4},
            reader_factory=_FailingReader,
        )

        self.assertEqual(
            reader.read_once(),
            {
                "TEMP": 28.4,
                "STATE_A": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
