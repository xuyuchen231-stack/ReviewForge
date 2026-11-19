"""Load the skill's shared exact packet codec; no model calls or review loops."""
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / 'reviewforge/scripts/evidence_packet.py'
if _path.is_file():
    _spec = importlib.util.spec_from_file_location('_rf_exact_packet', _path)
    _codec = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_codec)
    packet_view = _codec.packet_view
    expand_packet = _codec.expand_packet
else:
    # A standalone legacy runtime without the optional skill keeps its old wire.
    def packet_view(payload): return payload
    def expand_packet(payload): return payload
