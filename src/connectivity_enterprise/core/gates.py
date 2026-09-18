from pathlib import Path
import json
from datetime import datetime, timezone

from .paths import assert_output_path


VALID = {"PASS", "WARN", "FAIL", "BLOCKED", "NOT_RUN_DUE_TO_FAILED_GATE"}


class GateBook:
    def __init__(self, run_id, path):
        self.run_id = run_id
        self.path = assert_output_path(path)
        self.gates = {}

    def set(self, gate, status, finding, evidence=None):
        if status not in VALID:
            raise ValueError(f"Invalid gate status: {status}")
        self.gates[gate] = {
            "status": status,
            "finding": finding,
            "evidence": evidence or {},
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        self.write()

    def is_pass(self, *gates):
        return all(self.gates.get(g, {}).get("status") == "PASS" for g in gates)

    def write(self):
        payload = {"run_id": self.run_id, "gates": self.gates}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
