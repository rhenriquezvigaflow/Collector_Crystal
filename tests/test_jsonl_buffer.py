from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storage import jsonl_buffer


def _payload(lagoon_id: str, seq: int) -> str:
    return json.dumps(
        {
            "lagoon_id": lagoon_id,
            "source": "rockwell",
            "timestamp": f"2026-04-11T18:00:0{seq}Z",
            "tags": {"seq": seq},
        }
    )


class JsonlBufferTests(unittest.TestCase):
    def test_migrate_legacy_buffer_splits_entries_by_lagoon(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            legacy_path = base_dir / "buffer.jsonl"
            spool_dir = base_dir / "spool"
            legacy_path.write_text(
                "\n".join([_payload("lagoon-a", 1), _payload("lagoon-b", 2)]) + "\n",
                encoding="utf-8",
            )

            migrated = jsonl_buffer.migrate_legacy_buffer(
                legacy_path=legacy_path,
                base_dir=spool_dir,
            )

            self.assertEqual(migrated, {"lagoon-a": 1, "lagoon-b": 1})
            self.assertFalse(legacy_path.exists())
            self.assertTrue(
                jsonl_buffer.spool_path_for_lagoon("lagoon-a", spool_dir).exists()
            )
            self.assertTrue(
                jsonl_buffer.spool_path_for_lagoon("lagoon-b", spool_dir).exists()
            )

    def test_replay_for_lagoon_requeues_unsent_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spool_dir = Path(tmpdir)
            target_path = jsonl_buffer.spool_path_for_lagoon("lagoon-a", spool_dir)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(
                "\n".join([_payload("lagoon-a", 1), _payload("lagoon-a", 2)]) + "\n",
                encoding="utf-8",
            )

            seen: list[int] = []

            def _send(payload: dict) -> bool:
                seen.append(int(payload["tags"]["seq"]))
                return payload["tags"]["seq"] == 1

            replayed, pending, dropped = jsonl_buffer.replay_for_lagoon(
                lagoon_id="lagoon-a",
                send_payload=_send,
                max_items=10,
                base_dir=spool_dir,
            )

            self.assertEqual(replayed, 1)
            self.assertEqual(pending, 1)
            self.assertEqual(dropped, 0)
            self.assertEqual(seen, [1, 2])
            self.assertIn('"seq": 2', target_path.read_text(encoding="utf-8"))

    def test_replay_for_lagoon_drops_payloads_marked_for_discard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spool_dir = Path(tmpdir)
            target_path = jsonl_buffer.spool_path_for_lagoon("lagoon-a", spool_dir)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(
                "\n".join(
                    [
                        _payload("lagoon-a", 1),
                        _payload("lagoon-a", 2),
                        _payload("lagoon-a", 3),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            def _send(payload: dict) -> str:
                if payload["tags"]["seq"] < 3:
                    return "drop"
                return "keep"

            replayed, pending, dropped = jsonl_buffer.replay_for_lagoon(
                lagoon_id="lagoon-a",
                send_payload=_send,
                max_items=10,
                base_dir=spool_dir,
            )

            self.assertEqual(replayed, 0)
            self.assertEqual(pending, 1)
            self.assertEqual(dropped, 2)
            spool_text = target_path.read_text(encoding="utf-8")
            self.assertNotIn('"seq": 1', spool_text)
            self.assertNotIn('"seq": 2', spool_text)
            self.assertIn('"seq": 3', spool_text)


if __name__ == "__main__":
    unittest.main()
