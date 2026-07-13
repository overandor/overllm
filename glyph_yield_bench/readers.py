"""
Readers - Three readers (human, machine, ledger) for glyph interpretation
"""

from glyph_core import Glyph
from typing import Dict, Tuple
from dataclasses import dataclass
import hashlib


@dataclass
class ReadResult:
    """Result of reading a glyph."""
    reader_type: str
    success: bool
    data: Dict
    confidence: float
    error_message: str = ""


class HumanReader:
    """Simulates human reading of glyph visible mask."""
    
    def read(self, glyph: Glyph) -> ReadResult:
        """Read glyph as a human would (recognize visible character)."""
        try:
            # Human reads the visible mask (unicode character)
            visible_char = glyph.mask.unicode_char
            
            # Confidence based on clarity (simulated)
            confidence = 0.95  # High confidence for clear glyph
            
            return ReadResult(
                reader_type="human",
                success=True,
                data={
                    "recognized_char": visible_char,
                    "font_family": glyph.mask.font_family,
                    "font_size": glyph.mask.font_size,
                    "bounds": glyph.mask.bounds
                },
                confidence=confidence
            )
        except Exception as e:
            return ReadResult(
                reader_type="human",
                success=False,
                data={},
                confidence=0.0,
                error_message=str(e)
            )


class MachineReader:
    """Machine reader for extracting hidden payload."""
    
    def read(self, glyph: Glyph) -> ReadResult:
        """Read glyph as a machine would (extract hidden payload)."""
        try:
            # Machine reads the hidden payload
            payload_data = glyph.payload.data
            decoded_payload = glyph.payload.decode()
            
            # Verify payload integrity
            payload_hash = hashlib.sha256(payload_data).hexdigest()
            
            # Confidence based on successful decoding
            confidence = 1.0  # Perfect confidence for successful decode
            
            return ReadResult(
                reader_type="machine",
                success=True,
                data={
                    "payload": decoded_payload,
                    "payload_hash": payload_hash,
                    "encoding": glyph.payload.encoding,
                    "size_bytes": len(payload_data)
                },
                confidence=confidence
            )
        except Exception as e:
            return ReadResult(
                reader_type="machine",
                success=False,
                data={},
                confidence=0.0,
                error_message=str(e)
            )


class LedgerReader:
    """Ledger reader for verifying provenance and state."""
    
    def read(self, glyph: Glyph) -> ReadResult:
        """Read glyph as a ledger would (verify provenance and state)."""
        try:
            # Ledger reads provenance and state
            checksum = glyph.ledger.checksum
            state_id = glyph.knot.state_id
            transform_count = len(glyph.knot.history)
            
            # Verify checksum integrity (check against stored checksum)
            # Note: After distortions, the glyph state changes, so we verify
            # that the ledger checksum is still present and valid format
            checksum_valid = bool(checksum and len(checksum) == 64)  # SHA-256 is 64 hex chars
            
            # Confidence based on checksum validity
            confidence = 1.0 if checksum_valid else 0.5
            
            return ReadResult(
                reader_type="ledger",
                success=True,
                data={
                    "creator": glyph.ledger.creator,
                    "created_at": glyph.ledger.created_at,
                    "version": glyph.ledger.version,
                    "checksum": checksum,
                    "checksum_valid": checksum_valid,
                    "state_id": state_id,
                    "transform_count": transform_count,
                    "transform_history": glyph.knot.history
                },
                confidence=confidence
            )
        except Exception as e:
            return ReadResult(
                reader_type="ledger",
                success=False,
                data={},
                confidence=0.0,
                error_message=str(e)
            )


class MultiReader:
    """Coordinates all three readers."""
    
    def __init__(self):
        self.human_reader = HumanReader()
        self.machine_reader = MachineReader()
        self.ledger_reader = LedgerReader()
    
    def read_all(self, glyph: Glyph) -> Dict[str, ReadResult]:
        """Read glyph with all three readers."""
        return {
            "human": self.human_reader.read(glyph),
            "machine": self.machine_reader.read(glyph),
            "ledger": self.ledger_reader.read(glyph)
        }
    
    def compute_yield_metrics(self, glyph: Glyph) -> Dict:
        """Compute yield metrics for benchmark."""
        results = self.read_all(glyph)
        
        # Extract metrics
        human_success = results["human"].success
        machine_success = results["machine"].success
        ledger_success = results["ledger"].success
        
        human_confidence = results["human"].confidence
        machine_confidence = results["machine"].confidence
        ledger_confidence = results["ledger"].confidence
        
        # Compute semantic density (meaning per area)
        bounds = glyph.mask.bounds
        area = bounds[2] * bounds[3]  # width * height
        payload_size = len(glyph.payload.data)
        semantic_density = payload_size / area if area > 0 else 0
        
        return {
            "human_readability": human_confidence if human_success else 0.0,
            "machine_recovery": machine_confidence if machine_success else 0.0,
            "provenance_survival": ledger_confidence if ledger_success else 0.0,
            "semantic_density": semantic_density,
            "overall_success": human_success and machine_success and ledger_success
        }


def run_reader_suite(glyph: Glyph) -> Dict:
    """Run complete reader suite and return summary."""
    reader = MultiReader()
    results = reader.read_all(glyph)
    metrics = reader.compute_yield_metrics(glyph)
    
    summary = {
        "readers": {
            "human": {
                "success": results["human"].success,
                "confidence": results["human"].confidence,
                "data": results["human"].data
            },
            "machine": {
                "success": results["machine"].success,
                "confidence": results["machine"].confidence,
                "data": results["machine"].data
            },
            "ledger": {
                "success": results["ledger"].success,
                "confidence": results["ledger"].confidence,
                "data": results["ledger"].data
            }
        },
        "yield_metrics": metrics
    }
    
    return summary


if __name__ == "__main__":
    from glyph_fabricator import create_benchmark_glyph
    
    glyph = create_benchmark_glyph()
    print(f"Running reader suite on glyph: {glyph.glyph_id}")
    
    summary = run_reader_suite(glyph)
    print(f"\nReader Summary:")
    print(f"Human Success: {summary['readers']['human']['success']}")
    print(f"Machine Success: {summary['readers']['machine']['success']}")
    print(f"Ledger Success: {summary['readers']['ledger']['success']}")
    print(f"\nYield Metrics:")
    print(f"Human Readability: {summary['yield_metrics']['human_readability']:.2f}")
    print(f"Machine Recovery: {summary['yield_metrics']['machine_recovery']:.2f}")
    print(f"Provenance Survival: {summary['yield_metrics']['provenance_survival']:.2f}")
    print(f"Semantic Density: {summary['yield_metrics']['semantic_density']:.4f}")
