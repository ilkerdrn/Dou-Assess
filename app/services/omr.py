from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import re
from typing import Any

import cv2
import fitz  # PyMuPDF
import numpy as np

CANONICAL_DPI = 220
QR_PREFIX = "DOUASSESS|v1|"


class OMRProcessingError(ValueError):
    pass


@dataclass
class QRInfo:
    exam_id: int
    booklet: str
    token: str
    payload: str


def parse_qr_payload(payload: str | None) -> QRInfo | None:
    if not payload or not payload.startswith(QR_PREFIX):
        return None
    m = re.fullmatch(r"DOUASSESS\|v1\|exam=(\d+)\|booklet=([A-D])\|token=([A-Fa-f0-9]{8,64})", payload.strip())
    if not m:
        return None
    return QRInfo(exam_id=int(m.group(1)), booklet=m.group(2), token=m.group(3), payload=payload.strip())


def render_upload(data: bytes, filename: str) -> list[np.ndarray]:
    """Render an ADF PDF or decode a camera/image upload into BGR pages."""
    lower = (filename or "").lower()
    if lower.endswith(".pdf") or data.startswith(b"%PDF"):
        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise OMRProcessingError(f"PDF açılamadı: {exc}") from exc
        pages: list[np.ndarray] = []
        zoom = CANONICAL_DPI / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csRGB)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            pages.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
        return pages
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise OMRProcessingError("Görsel dosyası okunamadı")
    return [image]


def image_sha256(image: np.ndarray) -> str:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        return sha256(image.tobytes()).hexdigest()
    return sha256(encoded.tobytes()).hexdigest()


def _shrink_for_qr(image: np.ndarray, max_dim: int = 1800) -> np.ndarray:
    h, w = image.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale >= 0.999:
        return image
    return cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def decode_qr(image: np.ndarray) -> str | None:
    detector = cv2.QRCodeDetector()
    h, w = image.shape[:2]
    attempts: list[np.ndarray] = []
    # OpenCV QR decoding is scale-sensitive. Keep the original image and add a few
    # deterministic downscaled variants rather than relying on one resize.
    if max(h, w) <= 5000:
        attempts.append(image)
    for max_dim in (2400, 1800, 1400):
        scale = min(1.0, max_dim / max(h, w))
        if scale < 0.98:
            attempts.append(cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA))
    for test in attempts:
        for candidate in (test, cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)):
            try:
                data, _, _ = detector.detectAndDecode(candidate)
            except Exception:
                data = ""
            if data:
                return data.strip()
    return None


def decode_qr_oriented(image: np.ndarray) -> tuple[str | None, np.ndarray, int]:
    """Return QR payload and an orientation normalized for the v2 form.

    The QR lives in the right/lower half of the A4 page. We try four rotations and
    prefer the orientation that places the decoded QR back in that expected region.
    """
    rotations = [
        (0, image),
        (90, cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)),
        (180, cv2.rotate(image, cv2.ROTATE_180)),
        (270, cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)),
    ]
    detector = cv2.QRCodeDetector()
    fallback = None
    for degrees, candidate in rotations:
        h, w = candidate.shape[:2]
        attempts = [candidate]
        if max(h, w) > 2400:
            scale = 2400 / max(h, w)
            attempts.append(cv2.resize(candidate, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA))
        for test in attempts:
            try:
                data, points, _ = detector.detectAndDecode(test)
            except Exception:
                data, points = "", None
            if not data:
                continue
            if fallback is None:
                fallback = (data.strip(), candidate, degrees)
            if points is not None:
                pts = np.asarray(points).reshape(-1,2)
                cx = float(np.mean(pts[:,0])) / test.shape[1]
                cy = float(np.mean(pts[:,1])) / test.shape[0]
                if cx > 0.55 and cy > 0.48:
                    return data.strip(), candidate, degrees
    if fallback:
        return fallback
    return None, image, 0


def _pdf_to_px(point: list[float] | tuple[float, float], page_w: float, page_h: float, px_w: int, px_h: int) -> tuple[float, float]:
    x, y = float(point[0]), float(point[1])
    return x / page_w * px_w, (page_h - y) / page_h * px_h


def _marker_candidates(image: np.ndarray) -> list[tuple[float, float, float]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Otsu is intentionally global: registration marks are pure black and survive ADF scans well.
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    image_area = float(h * w)
    out: list[tuple[float, float, float]] = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = float(cw * ch)
        if area < image_area * 0.000008 or area > image_area * 0.0025:
            continue
        ratio = cw / max(ch, 1)
        if not 0.68 <= ratio <= 1.32:
            continue
        contour_area = cv2.contourArea(cnt)
        if contour_area / max(area, 1) < 0.55:
            continue
        out.append((x + cw / 2.0, y + ch / 2.0, area))
    return out


def rectify_page(image: np.ndarray, layout: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    page_w = float(layout["page_width"])
    page_h = float(layout["page_height"])
    canonical_w = int(round(page_w / 72.0 * CANONICAL_DPI))
    canonical_h = int(round(page_h / 72.0 * CANONICAL_DPI))
    expected = np.array([
        _pdf_to_px(p, page_w, page_h, canonical_w, canonical_h)
        for p in layout["marker_centers"]
    ], dtype=np.float32)

    candidates = _marker_candidates(image)
    ih, iw = image.shape[:2]
    expected_norm = expected / np.array([[canonical_w, canonical_h]], dtype=np.float32)
    chosen: list[tuple[float, float]] = []
    used: set[int] = set()
    distances: list[float] = []
    for ex, ey in expected_norm:
        best_i = None
        best_d = 999.0
        for i, (cx, cy, _) in enumerate(candidates):
            if i in used:
                continue
            nx, ny = cx / iw, cy / ih
            d = float(((nx - ex) ** 2 + (ny - ey) ** 2) ** 0.5)
            if d < best_d:
                best_i, best_d = i, d
        if best_i is None or best_d > 0.12:
            raise OMRProcessingError(f"Köşe işaretleri güvenilir biçimde bulunamadı ({len(chosen)}/4)")
        used.add(best_i)
        cx, cy, _ = candidates[best_i]
        chosen.append((cx, cy)); distances.append(best_d)

    actual = np.array(chosen, dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(actual, expected)
    warped = cv2.warpPerspective(image, matrix, (canonical_w, canonical_h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    return warped, {
        "marker_candidates": len(candidates),
        "marker_distances": [round(x, 5) for x in distances],
        "canonical_size": [canonical_w, canonical_h],
    }


def _bubble_darkness(gray: np.ndarray, pdf_circle: list[float], layout: dict[str, Any]) -> float:
    h, w = gray.shape[:2]
    page_w = float(layout["page_width"]); page_h = float(layout["page_height"])
    cx, cy = _pdf_to_px(pdf_circle[:2], page_w, page_h, w, h)
    r = float(pdf_circle[2]) / page_w * w
    sample_r = max(2, int(round(r * 0.50)))
    x0, x1 = max(0, int(cx) - sample_r), min(w, int(cx) + sample_r + 1)
    y0, y1 = max(0, int(cy) - sample_r), min(h, int(cy) + sample_r + 1)
    crop = gray[y0:y1, x0:x1]
    if crop.size == 0:
        return 0.0
    yy, xx = np.ogrid[:crop.shape[0], :crop.shape[1]]
    ccx = (crop.shape[1] - 1) / 2.0; ccy = (crop.shape[0] - 1) / 2.0
    mask = (xx - ccx) ** 2 + (yy - ccy) ** 2 <= sample_r ** 2
    values = crop[mask]
    if not values.size:
        return 0.0
    return float(1.0 - np.mean(values) / 255.0)


def _classify(scores: dict[str, float], threshold: float, gap: float) -> tuple[str | None, str, float]:
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked:
        return None, "blank", 0.0
    top_key, top = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    if top < threshold:
        return None, "blank", top
    if second >= threshold * 0.72 and top - second < gap:
        return None, "ambiguous", top - second
    confidence = min(1.0, max(0.0, (top - max(second, threshold * 0.5)) / max(0.001, 1.0 - threshold * 0.5)))
    return top_key, "marked", confidence


def read_omr(image: np.ndarray, layout: dict[str, Any]) -> dict[str, Any]:
    if layout.get("version") != "omr-v2":
        raise OMRProcessingError("Bu sınav kağıdı OMR v2 şablonunda değil")
    warped, registration = rectify_page(image, layout)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    issues: list[dict[str, Any]] = []
    student_digits: list[str] = []
    student_conf: list[float] = []
    student_metrics: dict[str, Any] = {}
    for pos in range(int(layout["student_digit_count"])):
        circles = layout["student_bubbles"][str(pos)]
        scores = {digit: _bubble_darkness(gray, circle, layout) for digit, circle in circles.items()}
        choice, state, conf = _classify(scores, threshold=0.25, gap=0.09)
        student_metrics[str(pos)] = {"scores": {k: round(v, 4) for k, v in scores.items()}, "state": state}
        if state != "marked" or choice is None:
            issues.append({"reason": "student_number", "position": pos + 1, "state": state})
            student_digits.append("?")
        else:
            student_digits.append(choice); student_conf.append(conf)

    booklet_scores = {k: _bubble_darkness(gray, circle, layout) for k, circle in layout.get("booklet_bubbles", {}).items()}
    booklet, booklet_state, booklet_conf = _classify(booklet_scores, threshold=0.45, gap=0.15)
    if booklet_state != "marked":
        issues.append({"reason": "booklet_bubble", "state": booklet_state})

    answers: dict[str, str | None] = {}
    answer_conf: list[float] = []
    answer_metrics: dict[str, Any] = {}
    for display_no, circles in layout.get("answer_bubbles", {}).items():
        scores = {letter: _bubble_darkness(gray, circle, layout) for letter, circle in circles.items()}
        choice, state, conf = _classify(scores, threshold=0.25, gap=0.10)
        answer_metrics[display_no] = {"scores": {k: round(v, 4) for k, v in scores.items()}, "state": state}
        if state == "ambiguous":
            issues.append({"reason": "answer_ambiguous", "question_no": int(display_no)})
            answers[display_no] = None
        else:
            answers[display_no] = choice  # blank is a legitimate unanswered question
            if state == "marked":
                answer_conf.append(conf)

    student_no = "".join(student_digits)
    overall = min(student_conf + answer_conf + ([booklet_conf] if booklet_state == "marked" else []) or [0.0])
    return {
        "student_no": student_no,
        "booklet_bubble": booklet,
        "answers_by_display_no": answers,
        "issues": issues,
        "confidence": {
            "overall": round(float(overall), 4),
            "student": round(float(min(student_conf) if student_conf else 0.0), 4),
            "answers": round(float(min(answer_conf) if answer_conf else 1.0), 4),
            "booklet": round(float(booklet_conf if booklet_state == "marked" else 0.0), 4),
        },
        "metrics": {
            "registration": registration,
            "student": student_metrics,
            "booklet": {"scores": {k: round(v, 4) for k, v in booklet_scores.items()}, "state": booklet_state},
            "answers": answer_metrics,
        },
        "warped": warped,
    }


def fill_bubble_for_test(image: np.ndarray, pdf_circle: list[float], layout: dict[str, Any], radius_factor: float = 0.62) -> None:
    """Test helper: mark a generated form at a known PDF coordinate."""
    h, w = image.shape[:2]
    cx, cy = _pdf_to_px(pdf_circle[:2], float(layout["page_width"]), float(layout["page_height"]), w, h)
    r = float(pdf_circle[2]) / float(layout["page_width"]) * w
    cv2.circle(image, (int(round(cx)), int(round(cy))), max(2, int(round(r * radius_factor))), (0, 0, 0), thickness=-1)
