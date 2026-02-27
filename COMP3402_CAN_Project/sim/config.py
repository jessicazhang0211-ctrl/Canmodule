from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class BusConfig:
	"""
	Bus configuration.

	Recommended defaults:
	- interface='socketcan'
	- channel='vcan0'
	NOTE: vcan has no real bitrate; bitrate is configured for real canX only.
	"""
	interface: str = "socketcan"         # 'socketcan' for Linux vcan0/can0 via SocketCAN
	channel: str = "vcan0"               # vcan0 recommended for safe simulation
	bitrate: int = 500000                # used for real canX config outside Python; kept for logs/metadata
	receive_own_messages: bool = False   # keep False unless you want loopback on same socket


@dataclass(frozen=True)
class ECUConfig:
	name: str
	arb_id: int
	period_s: float
	data_hex: str = "0000000000000000"   # 8 bytes hex string


@dataclass(frozen=True)
class DetectorConfig:
	window_s: float = 2.0
	# threshold is per-ID messages within window_s
	threshold: int = 80


@dataclass(frozen=True)
class FloodConfig:
	enabled: bool = True
	arb_id: int = 0x100
	rate_hz: int = 200
	duration_s: float = 5.0
	data_byte: int = 0x63


@dataclass(frozen=True)
class ExperimentConfig:
	bus: BusConfig = field(default_factory=BusConfig)
	ecus: List[ECUConfig] = field(default_factory=list)
	detector: DetectorConfig = field(default_factory=DetectorConfig)
	flood: FloodConfig = field(default_factory=FloodConfig)

	# phase timing
	baseline_s: float = 8.0
	recovery_s: float = 5.0

	# output
	out_dir: Path = Path("COMP3402_CAN_Project/evidence/logs")
	run_tag: str = "demo"
	allow_real_can: bool = False         # SAFETY: must be True to use can0/can1


def default_experiment() -> ExperimentConfig:
	"""
	A deterministic baseline profile: 3 periodic ECUs with different periods.
	Adjust arb_id/period to match your report narrative.
	"""
	ecus = [
		ECUConfig(name="ECU_FAST", arb_id=0x120, period_s=0.050, data_hex="0a00000000000000"),
		ECUConfig(name="ECU_MED",  arb_id=0x130, period_s=0.100, data_hex="0b00000000000000"),
		ECUConfig(name="ECU_SLOW", arb_id=0x140, period_s=0.200, data_hex="0c00000000000000"),
	]
	return ExperimentConfig(ecus=ecus)
