import os
from pathlib import Path
from typing import Dict, Any, Union, Tuple, Optional
import numpy as np
from backend.app.core.logging import logger

# Lazy load cv2 if installed
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV is not available; image preprocessing will operate in pass-through mode.")


class PreprocessingService:
    """
    Image enhancement and geometry correction service for document OCR.
    Handles:
    - Grayscale conversion
    - Noise filtering
    - Skew detection and deskewing
    - Contrast enhancement via CLAHE (Contrast Limited Adaptive Histogram Equalization)
    """

    def __init__(self, deskew_threshold_degrees: float = 0.5, max_skew_degrees: float = 45.0):
        self.deskew_threshold = deskew_threshold_degrees
        self.max_skew = max_skew_degrees

    def preprocess_image(
        self,
        image_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        apply_deskew: bool = True,
        apply_enhancement: bool = True
    ) -> Dict[str, Any]:
        """
        Executes full preprocessing pipeline on a document page image.

        Returns:
            Dict containing:
            - "success": bool
            - "original_path": str
            - "preprocessed_path": str
            - "width": int
            - "height": int
            - "skew_angle": float
            - "deskewed": bool
            - "enhanced": bool
        """
        in_path = Path(image_path)
        if not in_path.is_file():
            raise FileNotFoundError(f"Input image not found: {image_path}")

        if output_path is None:
            out_path = in_path.parent / f"prep_{in_path.name}"
        else:
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)

        if not OPENCV_AVAILABLE:
            logger.info("OpenCV not installed; skipping CV transformations.")
            return {
                "success": True,
                "original_path": str(in_path.resolve()),
                "preprocessed_path": str(in_path.resolve()),
                "width": 0,
                "height": 0,
                "skew_angle": 0.0,
                "deskewed": False,
                "enhanced": False,
                "note": "OpenCV pass-through"
            }

        # 1. Read image
        img = cv2.imread(str(in_path))
        if img is None:
            raise ValueError(f"OpenCV failed to decode image: {image_path}")

        orig_h, orig_w = img.shape[:2]
        skew_angle = 0.0
        deskewed = False
        enhanced = False

        # 2. Deskewing
        if apply_deskew:
            skew_angle, deskewed_img = self.detect_and_deskew(img)
            if abs(skew_angle) >= self.deskew_threshold and deskewed_img is not None:
                img = deskewed_img
                deskewed = True
                logger.info(f"Deskewed image by {skew_angle:.2f} degrees.")

        # 3. Contrast & Noise Enhancement
        if apply_enhancement:
            img = self.enhance_contrast_and_denoise(img)
            enhanced = True

        # 4. Save preprocessed image
        cv2.imwrite(str(out_path), img)
        final_h, final_w = img.shape[:2]

        return {
            "success": True,
            "original_path": str(in_path.resolve()),
            "preprocessed_path": str(out_path.resolve()),
            "width": final_w,
            "height": final_h,
            "skew_angle": round(skew_angle, 2),
            "deskewed": deskewed,
            "enhanced": enhanced
        }

    def detect_and_deskew(self, img: np.ndarray) -> Tuple[float, Optional[np.ndarray]]:
        """
        Calculates text orientation skew angle using minAreaRect on thresholded edges,
        and rotates the image to achieve upright alignment if within valid range.
        """
        if not OPENCV_AVAILABLE:
            return 0.0, None

        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Invert colors so text is foreground white, background is black
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Find coordinates of all white (text) pixels
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 50:
            return 0.0, None

        # Compute minimum bounding rectangle
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]

        # OpenCV minAreaRect returns angle in [-90, 0)
        # Normalize angle to [-45, 45] range
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Check bounds
        if abs(angle) < self.deskew_threshold or abs(angle) > self.max_skew:
            return 0.0, None

        # Rotate image around center
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(
            img,
            rot_mat,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return float(angle), deskewed

    def enhance_contrast_and_denoise(self, img: np.ndarray) -> np.ndarray:
        """
        Enhances document legibility using CLAHE and light Gaussian denoising.
        Preserves grayscale/color depth without producing harsh binary pixelation.
        """
        if not OPENCV_AVAILABLE:
            return img

        # Work in grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Light noise reduction
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # Contrast Limited Adaptive Histogram Equalization
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)

        # Convert back to 3-channel BGR for downstream models that expect 3 channels
        if len(img.shape) == 3:
            return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        return enhanced


preprocessing_service = PreprocessingService()

