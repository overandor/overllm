"""
Yield Benchmark - Main benchmark runner for GlyphYieldBench
"""

from glyph_core import Glyph
from glyph_fabricator import create_benchmark_glyph, GlyphFabricator
from distortion_engine import run_distortion_suite
from readers import run_reader_suite
from receipt_system import create_signed_receipt_chain, ReceiptSystem
from typing import Dict
import csv
import os
from datetime import datetime


class YieldBenchmark:
    """Main benchmark runner for GlyphYieldBench."""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def run_benchmark(self, glyph: Glyph = None) -> Dict:
        """Run complete benchmark suite on a glyph."""
        if glyph is None:
            glyph = create_benchmark_glyph()
        
        print(f"Running GlyphYieldBench on: {glyph.glyph_id}")
        
        # Step 1: Distortion tests
        print("\n1. Running distortion tests...")
        distortion_summary = run_distortion_suite(glyph)
        print(f"   Distortions: {distortion_summary['total_distortions']}")
        print(f"   Successful: {distortion_summary['successful']}")
        print(f"   Identity Preserved: {distortion_summary['identity_preserved']}")
        
        # Step 2: Reader tests
        print("\n2. Running reader tests...")
        reader_summary = run_reader_suite(glyph)
        yield_metrics = reader_summary["yield_metrics"]
        print(f"   Human Readability: {yield_metrics['human_readability']:.2f}")
        print(f"   Machine Recovery: {yield_metrics['machine_recovery']:.2f}")
        print(f"   Provenance Survival: {yield_metrics['provenance_survival']:.2f}")
        print(f"   Semantic Density: {yield_metrics['semantic_density']:.4f}")
        print(f"   Overall Success: {yield_metrics['overall_success']}")
        
        # Step 3: Generate receipts
        print("\n3. Generating signed receipts...")
        receipts = create_signed_receipt_chain(glyph, distortion_summary, yield_metrics)
        print(f"   Fabrication receipt: {receipts['fabrication'].receipt_id}")
        print(f"   Distortion receipt: {receipts['distortion'].receipt_id}")
        print(f"   Benchmark receipt: {receipts['benchmark'].receipt_id}")
        
        # Step 4: Save results
        print("\n4. Saving results...")
        self.save_yield_csv(glyph, distortion_summary, yield_metrics)
        self.save_glyph(glyph)
        self.save_receipts(receipts)
        
        # Compile final summary
        summary = {
            "glyph_id": glyph.glyph_id,
            "timestamp": datetime.utcnow().isoformat(),
            "distortion_summary": distortion_summary,
            "reader_summary": reader_summary,
            "yield_metrics": yield_metrics,
            "receipts": {
                "fabrication": receipts["fabrication"].receipt_id,
                "distortion": receipts["distortion"].receipt_id,
                "benchmark": receipts["benchmark"].receipt_id
            },
            "pass_criteria": self.evaluate_pass_criteria(yield_metrics)
        }
        
        print(f"\n5. Benchmark complete!")
        print(f"   Pass: {summary['pass_criteria']['passed']}")
        print(f"   Details: {summary['pass_criteria']['details']}")
        
        return summary
    
    def evaluate_pass_criteria(self, yield_metrics: Dict) -> Dict:
        """Evaluate whether glyph meets pass criteria."""
        # Thresholds (can be adjusted)
        theta_h = 0.8  # Human readability threshold
        theta_m = 0.9  # Machine recovery threshold
        theta_p = 0.9  # Provenance survival threshold
        theta_a = 0.005  # Semantic density threshold (adjusted for v0)
        
        human_pass = yield_metrics["human_readability"] >= theta_h
        machine_pass = yield_metrics["machine_recovery"] >= theta_m
        provenance_pass = yield_metrics["provenance_survival"] >= theta_p
        density_pass = yield_metrics["semantic_density"] >= theta_a
        
        overall_pass = human_pass and machine_pass and provenance_pass and density_pass
        
        return {
            "passed": overall_pass,
            "details": {
                "human_readability": {
                    "value": yield_metrics["human_readability"],
                    "threshold": theta_h,
                    "passed": human_pass
                },
                "machine_recovery": {
                    "value": yield_metrics["machine_recovery"],
                    "threshold": theta_m,
                    "passed": machine_pass
                },
                "provenance_survival": {
                    "value": yield_metrics["provenance_survival"],
                    "threshold": theta_p,
                    "passed": provenance_pass
                },
                "semantic_density": {
                    "value": yield_metrics["semantic_density"],
                    "threshold": theta_a,
                    "passed": density_pass
                }
            }
        }
    
    def save_yield_csv(self, glyph: Glyph, distortion_summary: Dict, yield_metrics: Dict):
        """Save yield metrics to CSV."""
        filepath = os.path.join(self.output_dir, "yield.csv")
        
        # Check if file exists to write header
        file_exists = os.path.isfile(filepath)
        
        with open(filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow([
                    "timestamp",
                    "glyph_id",
                    "total_distortions",
                    "successful_distortions",
                    "identity_preserved",
                    "human_readability",
                    "machine_recovery",
                    "provenance_survival",
                    "semantic_density",
                    "overall_success"
                ])
            
            writer.writerow([
                datetime.utcnow().isoformat(),
                glyph.glyph_id,
                distortion_summary["total_distortions"],
                distortion_summary["successful"],
                distortion_summary["identity_preserved"],
                yield_metrics["human_readability"],
                yield_metrics["machine_recovery"],
                yield_metrics["provenance_survival"],
                yield_metrics["semantic_density"],
                yield_metrics["overall_success"]
            ])
        
        print(f"   Saved yield metrics to: {filepath}")
    
    def save_glyph(self, glyph: Glyph):
        """Save glyph to JSON."""
        fabricator = GlyphFabricator()
        filepath = os.path.join(self.output_dir, f"{glyph.glyph_id}.json")
        fabricator.save_glyph(glyph, filepath)
        print(f"   Saved glyph to: {filepath}")
    
    def save_receipts(self, receipts: Dict):
        """Save all receipts to JSON."""
        system = ReceiptSystem()
        
        for receipt_type, receipt in receipts.items():
            filepath = os.path.join(self.output_dir, f"{receipt_type}_receipt.json")
            system.save_receipt(receipt, filepath)
            print(f"   Saved {receipt_type} receipt to: {filepath}")


def main():
    """Run GlyphYieldBench v0."""
    print("=" * 60)
    print("GlyphYieldBench v0")
    print("=" * 60)
    
    benchmark = YieldBenchmark()
    summary = benchmark.run_benchmark()
    
    print("\n" + "=" * 60)
    print("Benchmark Summary")
    print("=" * 60)
    print(f"Glyph ID: {summary['glyph_id']}")
    print(f"Timestamp: {summary['timestamp']}")
    print(f"Pass: {summary['pass_criteria']['passed']}")
    print(f"\nYield Metrics:")
    print(f"  Human Readability: {summary['yield_metrics']['human_readability']:.2f}")
    print(f"  Machine Recovery: {summary['yield_metrics']['machine_recovery']:.2f}")
    print(f"  Provenance Survival: {summary['yield_metrics']['provenance_survival']:.2f}")
    print(f"  Semantic Density: {summary['yield_metrics']['semantic_density']:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
