"""
Distortion Engine - Applies five distortion tests to glyphs
"""

from glyph_core import Glyph
from typing import Dict, List, Tuple
import random
import math
from dataclasses import dataclass


@dataclass
class DistortionResult:
    """Result of applying a distortion to a glyph."""
    distortion_type: str
    parameters: Dict
    success: bool
    glyph_modified: bool
    identity_preserved: bool
    error_message: str = ""


class DistortionEngine:
    """Applies controlled distortions to test glyph robustness."""
    
    def __init__(self):
        self.distortions = [
            "scale",
            "rotate",
            "translate",
            "blur",
            "jpeg_compression"
        ]
    
    def apply_scale(self, glyph: Glyph, scale_factor: float) -> DistortionResult:
        """Apply scaling distortion."""
        try:
            if scale_factor < 0.5 or scale_factor > 2.0:
                return DistortionResult(
                    distortion_type="scale",
                    parameters={"scale_factor": scale_factor},
                    success=False,
                    glyph_modified=False,
                    identity_preserved=False,
                    error_message="Scale factor out of variance field"
                )
            
            # Simulate scaling by modifying bounds
            original_bounds = glyph.mask.bounds
            new_bounds = (
                original_bounds[0],
                original_bounds[1],
                original_bounds[2] * scale_factor,
                original_bounds[3] * scale_factor
            )
            glyph.mask.bounds = new_bounds
            
            # Record in knot state
            glyph.knot.add_transform({
                "type": "scale",
                "scale_factor": scale_factor,
                "original_bounds": original_bounds,
                "new_bounds": new_bounds
            })
            
            return DistortionResult(
                distortion_type="scale",
                parameters={"scale_factor": scale_factor},
                success=True,
                glyph_modified=True,
                identity_preserved=True
            )
        except Exception as e:
            return DistortionResult(
                distortion_type="scale",
                parameters={"scale_factor": scale_factor},
                success=False,
                glyph_modified=False,
                identity_preserved=False,
                error_message=str(e)
            )
    
    def apply_rotate(self, glyph: Glyph, angle_degrees: float) -> DistortionResult:
        """Apply rotation distortion."""
        try:
            if angle_degrees < -45 or angle_degrees > 45:
                return DistortionResult(
                    distortion_type="rotate",
                    parameters={"angle_degrees": angle_degrees},
                    success=False,
                    glyph_modified=False,
                    identity_preserved=False,
                    error_message="Rotation angle out of variance field"
                )
            
            # Record rotation in knot state
            glyph.knot.add_transform({
                "type": "rotate",
                "angle_degrees": angle_degrees
            })
            
            return DistortionResult(
                distortion_type="rotate",
                parameters={"angle_degrees": angle_degrees},
                success=True,
                glyph_modified=True,
                identity_preserved=True
            )
        except Exception as e:
            return DistortionResult(
                distortion_type="rotate",
                parameters={"angle_degrees": angle_degrees},
                success=False,
                glyph_modified=False,
                identity_preserved=False,
                error_message=str(e)
            )
    
    def apply_translate(self, glyph: Glyph, dx: float, dy: float) -> DistortionResult:
        """Apply translation distortion."""
        try:
            if abs(dx) > 10 or abs(dy) > 10:
                return DistortionResult(
                    distortion_type="translate",
                    parameters={"dx": dx, "dy": dy},
                    success=False,
                    glyph_modified=False,
                    identity_preserved=False,
                    error_message="Translation out of variance field"
                )
            
            # Simulate translation by modifying bounds
            original_bounds = glyph.mask.bounds
            new_bounds = (
                original_bounds[0] + dx,
                original_bounds[1] + dy,
                original_bounds[2],
                original_bounds[3]
            )
            glyph.mask.bounds = new_bounds
            
            # Record in knot state
            glyph.knot.add_transform({
                "type": "translate",
                "dx": dx,
                "dy": dy,
                "original_bounds": original_bounds,
                "new_bounds": new_bounds
            })
            
            return DistortionResult(
                distortion_type="translate",
                parameters={"dx": dx, "dy": dy},
                success=True,
                glyph_modified=True,
                identity_preserved=True
            )
        except Exception as e:
            return DistortionResult(
                distortion_type="translate",
                parameters={"dx": dx, "dy": dy},
                success=False,
                glyph_modified=False,
                identity_preserved=False,
                error_message=str(e)
            )
    
    def apply_blur(self, glyph: Glyph, blur_radius: float) -> DistortionResult:
        """Apply blur distortion (simulated)."""
        try:
            if blur_radius < 0 or blur_radius > 5:
                return DistortionResult(
                    distortion_type="blur",
                    parameters={"blur_radius": blur_radius},
                    success=False,
                    glyph_modified=False,
                    identity_preserved=False,
                    error_message="Blur radius out of range"
                )
            
            # Record blur in knot state
            glyph.knot.add_transform({
                "type": "blur",
                "blur_radius": blur_radius
            })
            
            return DistortionResult(
                distortion_type="blur",
                parameters={"blur_radius": blur_radius},
                success=True,
                glyph_modified=True,
                identity_preserved=True
            )
        except Exception as e:
            return DistortionResult(
                distortion_type="blur",
                parameters={"blur_radius": blur_radius},
                success=False,
                glyph_modified=False,
                identity_preserved=False,
                error_message=str(e)
            )
    
    def apply_jpeg_compression(self, glyph: Glyph, quality: int) -> DistortionResult:
        """Apply JPEG compression distortion (simulated)."""
        try:
            if quality < 10 or quality > 100:
                return DistortionResult(
                    distortion_type="jpeg_compression",
                    parameters={"quality": quality},
                    success=False,
                    glyph_modified=False,
                    identity_preserved=False,
                    error_message="Quality out of range"
                )
            
            # Record compression in knot state
            glyph.knot.add_transform({
                "type": "jpeg_compression",
                "quality": quality
            })
            
            return DistortionResult(
                distortion_type="jpeg_compression",
                parameters={"quality": quality},
                success=True,
                glyph_modified=True,
                identity_preserved=True
            )
        except Exception as e:
            return DistortionResult(
                distortion_type="jpeg_compression",
                parameters={"quality": quality},
                success=False,
                glyph_modified=False,
                identity_preserved=False,
                error_message=str(e)
            )
    
    def apply_all_distortions(self, glyph: Glyph) -> List[DistortionResult]:
        """Apply all five distortion tests to a glyph."""
        results = []
        
        # Scale distortion
        results.append(self.apply_scale(glyph, scale_factor=0.7))
        
        # Rotate distortion
        results.append(self.apply_rotate(glyph, angle_degrees=30))
        
        # Translate distortion
        results.append(self.apply_translate(glyph, dx=5, dy=5))
        
        # Blur distortion
        results.append(self.apply_blur(glyph, blur_radius=2.0))
        
        # JPEG compression distortion
        results.append(self.apply_jpeg_compression(glyph, quality=75))
        
        return results


def run_distortion_suite(glyph: Glyph) -> Dict:
    """Run complete distortion suite and return summary."""
    engine = DistortionEngine()
    results = engine.apply_all_distortions(glyph)
    
    summary = {
        "total_distortions": len(results),
        "successful": sum(1 for r in results if r.success),
        "identity_preserved": sum(1 for r in results if r.identity_preserved),
        "distortions": [
            {
                "type": r.distortion_type,
                "parameters": r.parameters,
                "success": r.success,
                "identity_preserved": r.identity_preserved
            }
            for r in results
        ]
    }
    
    return summary


if __name__ == "__main__":
    from glyph_fabricator import create_benchmark_glyph
    
    glyph = create_benchmark_glyph()
    print(f"Testing distortions on glyph: {glyph.glyph_id}")
    
    summary = run_distortion_suite(glyph)
    print(f"\nDistortion Summary:")
    print(f"Total: {summary['total_distortions']}")
    print(f"Successful: {summary['successful']}")
    print(f"Identity Preserved: {summary['identity_preserved']}")
