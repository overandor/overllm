"""
GlyphYieldBench Core Object Model

A glyph is a fabricated computational object:
G = (M, P, V, K, L)

Where:
- M = visible_mask (what humans recognize)
- P = hidden_payload (machine-readable substrate)
- V = variance_field (legal deformation space)
- K = knot_state (transformation history)
- L = ledger (provenance and receipts)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import hashlib
import json
from datetime import datetime


@dataclass
class VisibleMask:
    """The visible geometry that a human immediately recognizes."""
    unicode_char: str
    font_family: str = "Arial"
    font_size: int = 24
    color: str = "#000000"
    bounds: tuple = (0, 0, 100, 100)  # x, y, width, height
    
    def to_dict(self) -> Dict:
        return {
            "unicode_char": self.unicode_char,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "color": self.color,
            "bounds": self.bounds
        }


@dataclass
class HiddenPayload:
    """Machine-readable or structured information associated with the glyph."""
    data: bytes
    encoding: str = "utf-8"
    compression: str = "none"
    
    def to_dict(self) -> Dict:
        return {
            "data_hash": hashlib.sha256(self.data).hexdigest(),
            "encoding": self.encoding,
            "compression": self.compression,
            "size_bytes": len(self.data)
        }
    
    def decode(self) -> str:
        return self.data.decode(self.encoding)


@dataclass
class VarianceField:
    """The admissible deformation space that preserves identity."""
    allowed_transforms: List[str] = field(default_factory=lambda: [
        "scale_0.5_to_2.0",
        "rotate_-45_to_45",
        "translate_-10_to_10",
        "opacity_0.5_to_1.0"
    ])
    max_distortion: float = 0.3  # Maximum allowed distortion before identity loss
    
    def to_dict(self) -> Dict:
        return {
            "allowed_transforms": self.allowed_transforms,
            "max_distortion": self.max_distortion
        }


@dataclass
class KnotState:
    """The glyph's transformation history or configuration."""
    state_id: str
    history: List[Dict] = field(default_factory=list)
    current_transform: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "state_id": self.state_id,
            "history": self.history,
            "current_transform": self.current_transform
        }
    
    def add_transform(self, transform: Dict):
        self.history.append({
            "transform": transform,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.current_transform = transform


@dataclass
class Ledger:
    """Provenance and reproducibility metadata."""
    creator: str
    created_at: str
    version: str = "0.1"
    checksum: str = ""
    signature: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "creator": self.creator,
            "created_at": self.created_at,
            "version": self.version,
            "checksum": self.checksum,
            "signature": self.signature
        }
    
    def compute_checksum(self, glyph_data: Dict) -> str:
        """Compute SHA-256 checksum of glyph data."""
        data_str = json.dumps(glyph_data, sort_keys=True)
        self.checksum = hashlib.sha256(data_str.encode()).hexdigest()
        return self.checksum


@dataclass
class Glyph:
    """Complete glyph object: G = (M, P, V, K, L)"""
    glyph_id: str
    mask: VisibleMask
    payload: HiddenPayload
    variance: VarianceField
    knot: KnotState
    ledger: Ledger
    
    def to_dict(self) -> Dict:
        """Serialize glyph to dictionary."""
        return {
            "glyph_id": self.glyph_id,
            "mask": self.mask.to_dict(),
            "payload": self.payload.to_dict(),
            "variance": self.variance.to_dict(),
            "knot": self.knot.to_dict(),
            "ledger": self.ledger.to_dict()
        }
    
    def compute_checksum(self) -> str:
        """Compute and store checksum."""
        data = self.to_dict()
        return self.ledger.compute_checksum(data)
    
    def to_json(self) -> str:
        """Serialize glyph to JSON."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Glyph':
        """Deserialize glyph from JSON."""
        data = json.loads(json_str)
        return cls(
            glyph_id=data["glyph_id"],
            mask=VisibleMask(**data["mask"]),
            payload=HiddenPayload(**data["payload"]),
            variance=VarianceField(**data["variance"]),
            knot=KnotState(**data["knot"]),
            ledger=Ledger(**data["ledger"])
        )


def create_test_glyph(glyph_id: str = "test_glyph_001") -> Glyph:
    """Create a test glyph for benchmarking."""
    return Glyph(
        glyph_id=glyph_id,
        mask=VisibleMask(unicode_char="A"),
        payload=HiddenPayload(data=b"test_payload_123"),
        variance=VarianceField(),
        knot=KnotState(state_id=f"{glyph_id}_state_001"),
        ledger=Ledger(
            creator="GlyphYieldBench",
            created_at=datetime.utcnow().isoformat()
        )
    )
