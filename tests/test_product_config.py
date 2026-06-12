from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common.config import load_plc_configs, normalize_product_type, resolve_product_type


class ProductConfigTests(unittest.TestCase):
    def test_include_entry_can_override_product_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            config_dir = base_dir / "config"
            config_dir.mkdir()

            (config_dir / "small.yml").write_text(
                "\n".join(
                    [
                        'lagoon_id: "small-demo"',
                        'source: "siemens"',
                        'timezone: "America/Santiago"',
                        "tags: {}",
                    ]
                ),
                encoding="utf-8",
            )
            (config_dir / "crystal.yml").write_text(
                "\n".join(
                    [
                        'lagoon_id: "crystal-demo"',
                        'source: "rockwell"',
                        'timezone: "America/Santiago"',
                        "tags: {}",
                    ]
                ),
                encoding="utf-8",
            )
            master_path = base_dir / "collectors.yml"
            master_path.write_text(
                "\n".join(
                    [
                        'product_type: "crystal"',
                        "plcs:",
                        '  - include: "config/small.yml"',
                        '    product_type: "small"',
                        '  - include: "config/crystal.yml"',
                    ]
                ),
                encoding="utf-8",
            )

            configs, root = load_plc_configs(str(master_path))

            self.assertEqual(resolve_product_type(configs[0], root), "small")
            self.assertEqual(resolve_product_type(configs[1], root), "crystal")

    def test_product_type_is_normalized_and_validated(self) -> None:
        self.assertEqual(normalize_product_type(" Small "), "small")

        with self.assertRaises(ValueError):
            normalize_product_type("legacy", lagoon_id="lagoon-a")


if __name__ == "__main__":
    unittest.main()
