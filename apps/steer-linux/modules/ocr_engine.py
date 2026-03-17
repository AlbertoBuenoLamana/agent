"""OCR text recognition — replaces OCR.swift.

Uses pytesseract (Tesseract OCR) with Pillow for image loading.
"""

from dataclasses import dataclass

from .errors import OcrFailed


@dataclass
class OCRResult:
    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 2),
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


def recognize(image_path: str, min_confidence: float = 0.5) -> list[OCRResult]:
    """Extract text regions from image with bounding boxes and confidence."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise OcrFailed(f"OCR dependencies not installed: {e}")

    try:
        img = Image.open(image_path)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except Exception as e:
        raise OcrFailed(f"OCR failed on '{image_path}': {e}")

    results = []
    n_boxes = len(data["text"])

    for i in range(n_boxes):
        text = data["text"][i].strip()
        if not text:
            continue

        conf = float(data["conf"][i])
        # Tesseract returns confidence 0-100, normalize to 0-1
        if conf < 0:
            continue
        conf_normalized = conf / 100.0

        if conf_normalized < min_confidence:
            continue

        results.append(OCRResult(
            text=text,
            confidence=conf_normalized,
            x=int(data["left"][i]),
            y=int(data["top"][i]),
            width=int(data["width"][i]),
            height=int(data["height"][i]),
        ))

    # Merge adjacent words into lines based on vertical proximity
    results = _merge_lines(results)
    return results


def _merge_lines(results: list[OCRResult], y_threshold: int = 10) -> list[OCRResult]:
    """Merge OCR results that are on the same line into single entries."""
    if not results:
        return results

    sorted_results = sorted(results, key=lambda r: (r.y, r.x))
    merged = []
    current = sorted_results[0]

    for r in sorted_results[1:]:
        if abs(r.y - current.y) < y_threshold:
            # Same line — merge
            new_x = min(current.x, r.x)
            new_y = min(current.y, r.y)
            new_right = max(current.x + current.width, r.x + r.width)
            new_bottom = max(current.y + current.height, r.y + r.height)
            current = OCRResult(
                text=current.text + " " + r.text,
                confidence=min(current.confidence, r.confidence),
                x=new_x,
                y=new_y,
                width=new_right - new_x,
                height=new_bottom - new_y,
            )
        else:
            merged.append(current)
            current = r

    merged.append(current)
    return merged


def to_elements(results: list[OCRResult]) -> list[dict]:
    """Convert OCR results to UIElement dicts with O1, O2, etc. IDs."""
    elements = []
    for i, r in enumerate(results, 1):
        elements.append({
            "id": f"O{i}",
            "role": "ocrtext",
            "label": r.text,
            "value": None,
            "x": r.x,
            "y": r.y,
            "width": r.width,
            "height": r.height,
            "isEnabled": True,
            "depth": 0,
        })
    return elements
