"""
Glyph Fabricator - Creates and compiles glyph objects
"""

from glyph_core import Glyph, VisibleMask, HiddenPayload, VarianceField, KnotState, Ledger
from typing import Dict, Optional
import json
from datetime import datetime


class GlyphFabricator:
    """Compiles glyph objects from specifications."""
    
    def __init__(self, creator: str = "GlyphYieldBench"):
        self.creator = creator
    
    def fabricate_glyph(
        self,
        glyph_id: str,
        unicode_char: str,
        payload_data: bytes,
        font_family: str = "Arial",
        font_size: int = 24,
        allowed_transforms: Optional[list] = None
    ) -> Glyph:
        """Fabricate a complete glyph object."""
        
        if allowed_transforms is None:
            allowed_transforms = [
                "scale_0.5_to_2.0",
                "rotate_-45_to_45",
                "translate_-10_to_10",
                "opacity_0.5_to_1.0"
            ]
        
        glyph = Glyph(
            glyph_id=glyph_id,
            mask=VisibleMask(
                unicode_char=unicode_char,
                font_family=font_family,
                font_size=font_size
            ),
            payload=HiddenPayload(data=payload_data),
            variance=VarianceField(allowed_transforms=allowed_transforms),
            knot=KnotState(state_id=f"{glyph_id}_state_001"),
            ledger=Ledger(
                creator=self.creator,
                created_at=datetime.utcnow().isoformat()
            )
        )
        
        # Compute checksum
        glyph.compute_checksum()
        
        return glyph
    
    def fabricate_macro_glyph(self) -> Glyph:
        """Create the initial macro glyph for benchmarking."""
        return self.fabricate_glyph(
            glyph_id="macro_glyph_001",
            unicode_char="Ω",  # Omega symbol for macro glyph
            payload_data=b"MACRO_GLYPH_PAYLOAD_V0_TEST_DATA_123456789"
        )
    
    def save_glyph(self, glyph: Glyph, filepath: str):
        """Save glyph to JSON file."""
        with open(filepath, 'w') as f:
            f.write(glyph.to_json())
    
    def load_glyph(self, filepath: str) -> Glyph:
        """Load glyph from JSON file."""
        with open(filepath, 'r') as f:
            return Glyph.from_json(f.read())


def create_benchmark_glyph() -> Glyph:
    """Create the benchmark glyph for GlyphYieldBench v0."""
    fabricator = GlyphFabricator()
    glyph = fabricator.fabricate_macro_glyph()
    return glyph


if __name__ == "__main__":
    # Create and save benchmark glyph
    glyph = create_benchmark_glyph()
    print(f"Created glyph: {glyph.glyph_id}")
    print(f"Checksum: {glyph.ledger.checksum}")
    print(f"Payload: {glyph.payload.decode()}")
    
    # Save to file
    fabricator = GlyphFabricator()
    fabricator.save_glyph(glyph, "results/macro_glyph_001.json")
    print("Saved to results/macro_glyph_001.json")
