from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Check:
    gate: str
    name: str
    status: str
    evidence: str
    severity: str = "info"
