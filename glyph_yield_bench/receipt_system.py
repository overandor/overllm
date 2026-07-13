"""
Receipt System - Generates signed receipts for glyph operations
"""

from glyph_core import Glyph
from typing import Dict
import hashlib
import json
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Receipt:
    """Signed receipt for glyph operations."""
    receipt_id: str
    glyph_id: str
    operation: str
    timestamp: str
    checksum: str
    signature: str
    metadata: Dict
    
    def to_dict(self) -> Dict:
        return {
            "receipt_id": self.receipt_id,
            "glyph_id": self.glyph_id,
            "operation": self.operation,
            "timestamp": self.timestamp,
            "checksum": self.checksum,
            "signature": self.signature,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class ReceiptSystem:
    """Generates and manages signed receipts."""
    
    def __init__(self, signer: str = "GlyphYieldBench"):
        self.signer = signer
    
    def generate_receipt(
        self,
        glyph: Glyph,
        operation: str,
        metadata: Dict = None
    ) -> Receipt:
        """Generate a signed receipt for a glyph operation."""
        if metadata is None:
            metadata = {}
        
        receipt_id = f"receipt_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{glyph.glyph_id}"
        timestamp = datetime.utcnow().isoformat()
        checksum = glyph.ledger.checksum
        
        # Create signature (simplified - in production use proper crypto)
        signature_data = f"{receipt_id}|{glyph.glyph_id}|{operation}|{timestamp}|{checksum}|{self.signer}"
        signature = hashlib.sha256(signature_data.encode()).hexdigest()
        
        receipt = Receipt(
            receipt_id=receipt_id,
            glyph_id=glyph.glyph_id,
            operation=operation,
            timestamp=timestamp,
            checksum=checksum,
            signature=signature,
            metadata=metadata
        )
        
        return receipt
    
    def generate_fabrication_receipt(self, glyph: Glyph) -> Receipt:
        """Generate receipt for glyph fabrication."""
        return self.generate_receipt(
            glyph,
            "fabrication",
            {
                "creator": glyph.ledger.creator,
                "version": glyph.ledger.version,
                "payload_size": len(glyph.payload.data)
            }
        )
    
    def generate_distortion_receipt(self, glyph: Glyph, distortion_summary: Dict) -> Receipt:
        """Generate receipt for distortion testing."""
        return self.generate_receipt(
            glyph,
            "distortion_test",
            {
                "total_distortions": distortion_summary["total_distortions"],
                "successful": distortion_summary["successful"],
                "identity_preserved": distortion_summary["identity_preserved"]
            }
        )
    
    def generate_benchmark_receipt(self, glyph: Glyph, yield_metrics: Dict) -> Receipt:
        """Generate receipt for benchmark completion."""
        return self.generate_receipt(
            glyph,
            "benchmark",
            {
                "human_readability": yield_metrics["human_readability"],
                "machine_recovery": yield_metrics["machine_recovery"],
                "provenance_survival": yield_metrics["provenance_survival"],
                "semantic_density": yield_metrics["semantic_density"],
                "overall_success": yield_metrics["overall_success"]
            }
        )
    
    def save_receipt(self, receipt: Receipt, filepath: str):
        """Save receipt to JSON file."""
        with open(filepath, 'w') as f:
            f.write(receipt.to_json())
    
    def load_receipt(self, filepath: str) -> Receipt:
        """Load receipt from JSON file."""
        with open(filepath, 'r') as f:
            data = json.loads(f.read())
            return Receipt(**data)


def create_signed_receipt_chain(glyph: Glyph, distortion_summary: Dict, yield_metrics: Dict) -> Dict:
    """Create a chain of signed receipts for complete benchmark."""
    system = ReceiptSystem()
    
    receipts = {
        "fabrication": system.generate_fabrication_receipt(glyph),
        "distortion": system.generate_distortion_receipt(glyph, distortion_summary),
        "benchmark": system.generate_benchmark_receipt(glyph, yield_metrics)
    }
    
    return receipts


if __name__ == "__main__":
    from glyph_fabricator import create_benchmark_glyph
    from distortion_engine import run_distortion_suite
    from readers import run_reader_suite
    
    glyph = create_benchmark_glyph()
    print(f"Creating receipt chain for glyph: {glyph.glyph_id}")
    
    distortion_summary = run_distortion_suite(glyph)
    reader_summary = run_reader_suite(glyph)
    yield_metrics = reader_summary["yield_metrics"]
    
    receipts = create_signed_receipt_chain(glyph, distortion_summary, yield_metrics)
    
    print(f"\nReceipt Chain:")
    for receipt_type, receipt in receipts.items():
        print(f"{receipt_type}: {receipt.receipt_id}")
        print(f"  Signature: {receipt.signature}")
