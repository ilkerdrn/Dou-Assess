from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re

import cv2
import fitz
import numpy as np

from ..config import settings
from ..security import validate_image_payload, validate_pdf_payload

CANON_W = 1200
CANON_H = 800


class ScanError(ValueError):
    pass


def iter_decode_upload(data: bytes, filename: str):
    """Yield scan pages one at a time to keep large ADF PDFs memory bounded."""
    ext = Path(filename or '').suffix.lower()
    if ext == '.pdf':
        try:
            validate_pdf_payload(data, purpose='Tarama PDF')
            doc = fitz.open(stream=data, filetype='pdf')
            try:
                if doc.needs_pass:
                    raise ScanError('Şifreli tarama PDF dosyaları kabul edilmez')
                mat = fitz.Matrix(2.3, 2.3)
                max_pixels = settings.max_image_megapixels * 1_000_000
                yielded = 0
                for page_no, page in enumerate(doc, start=1):
                    target_w = max(1, int(page.rect.width * 2.3))
                    target_h = max(1, int(page.rect.height * 2.3))
                    if target_w * target_h > max_pixels:
                        raise ScanError(f'{page_no}. sayfa işlenebilir görsel boyutu sınırını aşıyor')
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    arr = np.frombuffer(pix.tobytes('png'), np.uint8)
                    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if image is not None:
                        yielded += 1
                        yield image
                    del pix, arr, image
                if not yielded:
                    raise ScanError('PDF içinde okunabilir sayfa yok')
            finally:
                doc.close()
        except ScanError:
            raise
        except Exception as exc:
            detail = getattr(exc, 'detail', None)
            raise ScanError(str(detail or f'PDF okunamadı: {exc}')) from exc
        return
    if ext in {'.png', '.jpg', '.jpeg'}:
        try:
            validate_image_payload(data, purpose='Tarama görseli')
        except Exception as exc:
            detail = getattr(exc, 'detail', None)
            raise ScanError(str(detail or exc)) from exc
        arr = np.frombuffer(data, np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ScanError('Görsel okunamadı')
        yield image
        return
    raise ScanError('Tarama dosyası PDF, JPG veya PNG olmalıdır')


def decode_upload(data: bytes, filename: str) -> list[np.ndarray]:
    """Compatibility wrapper; scan ingestion uses the streaming iterator."""
    return list(iter_decode_upload(data, filename))


def decode_qr(image: np.ndarray) -> tuple[str | None, np.ndarray]:
    detector = cv2.QRCodeDetector()
    current = image
    for _ in range(4):
        try:
            value, points, _ = detector.detectAndDecode(current)
        except Exception:
            value, points = '', None
        if value:
            return value.strip(), current
        current = cv2.rotate(current, cv2.ROTATE_90_CLOCKWISE)
    return None, image


def parse_qr_payload(payload: str | None) -> dict:
    if not payload or not payload.startswith('DOUASSESS|'):
        return {}
    parts = payload.split('|')
    values = {}
    for part in parts[2:]:
        if '=' in part:
            k, v = part.split('=', 1)
            values[k] = v
    try:
        exam_id = int(values.get('exam', ''))
    except Exception:
        exam_id = None
    student_no = values.get('student')
    if student_no == '-':
        student_no = None
    try:
        logical_page_no = int(values.get('page', '')) if values.get('page') else None
    except Exception:
        logical_page_no = None
    raw_questions = values.get('questions') or ''
    question_numbers = []
    for part in raw_questions.split(','):
        try:
            if part.strip():
                question_numbers.append(int(part.strip()))
        except Exception:
            continue
    return {
        'exam_id': exam_id,
        'booklet': (values.get('booklet') or '').upper() or None,
        'token': values.get('token'),
        'student_no': student_no,
        'role': (values.get('role') or 'omr').lower(),
        'logical_page_no': logical_page_no,
        'question_numbers': question_numbers,
        'raw': payload,
    }


def _order_points(pts: np.ndarray) -> np.ndarray:
    pts = np.asarray(pts, dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).reshape(-1)
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def find_registration_marks(image: np.ndarray) -> np.ndarray | None:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 65, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(th, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    candidates = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        ratio = cw / max(ch, 1)
        fill = area / max(cw * ch, 1)
        if 12 <= cw <= w * .05 and 12 <= ch <= h * .05 and .78 <= ratio <= 1.28 and fill >= .80:
            cx, cy = x + cw / 2, y + ch / 2
            if cy >= h * .48:
                candidates.append((cx, cy, area))
    if len(candidates) < 4:
        return None
    # Find a top/bottom pair of long horizontal marker pairs whose x positions align.
    pairs=[]
    for i,a in enumerate(candidates):
        for b in candidates[i+1:]:
            left,right=(a,b) if a[0] < b[0] else (b,a)
            if abs(left[1]-right[1]) <= h*.025 and (right[0]-left[0]) >= w*.60:
                pairs.append((left,right))
    best=None; best_score=-1
    for i,top_pair in enumerate(pairs):
        for bottom_pair in pairs[i+1:]:
            tp,bp=(top_pair,bottom_pair) if sum(x[1] for x in top_pair) < sum(x[1] for x in bottom_pair) else (bottom_pair,top_pair)
            vertical=((bp[0][1]+bp[1][1])-(tp[0][1]+tp[1][1]))/2
            if vertical < h*.18:
                continue
            align=abs(tp[0][0]-bp[0][0])+abs(tp[1][0]-bp[1][0])
            if align > w*.06:
                continue
            span=(tp[1][0]-tp[0][0])+(bp[1][0]-bp[0][0])
            score=span+vertical-align*4
            if score>best_score:
                best_score=score; best=(tp,bp)
    if not best:
        return None
    top,bottom=best
    return np.array([[top[0][0],top[0][1]],[top[1][0],top[1][1]],[bottom[1][0],bottom[1][1]],[bottom[0][0],bottom[0][1]]],dtype=np.float32)


def warp_omr(image: np.ndarray, marks: np.ndarray) -> np.ndarray:
    src = _order_points(marks)
    dst = np.array([[0, 0], [CANON_W-1, 0], [CANON_W-1, CANON_H-1], [0, CANON_H-1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image, matrix, (CANON_W, CANON_H))


def _disc_darkness(gray: np.ndarray, x: int, y: int, radius: int = 12) -> float:
    yy, xx = np.ogrid[:gray.shape[0], :gray.shape[1]]
    mask = (xx-x)**2 + (yy-y)**2 <= radius**2
    vals = gray[mask]
    if vals.size == 0:
        return 0.0
    return float(np.mean(255 - vals) / 255.0)


def read_bubbles(warped: np.ndarray, metadata: dict) -> dict:
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    # normalize illumination before darkness measurement
    gray = cv2.GaussianBlur(gray, (3,3), 0)
    layout = metadata.get('omr_layout') or {}
    grouped: dict[int, list[dict]] = {}
    for bubble in layout.get('bubbles', []):
        x = int(float(bubble['x']) * (CANON_W-1))
        y = int(float(bubble['y']) * (CANON_H-1))
        score = _disc_darkness(gray, x, y, radius=11)
        grouped.setdefault(int(bubble['display_no']), []).append({'letter': bubble['letter'], 'score': score})
    answers = {}
    issues = []
    diagnostics = {}
    for no, opts in grouped.items():
        opts = sorted(opts, key=lambda x: x['score'], reverse=True)
        top = opts[0]
        second = opts[1] if len(opts) > 1 else {'score': 0}
        diagnostics[str(no)] = {x['letter']: round(x['score'], 4) for x in opts}
        # Printed ring contributes some darkness. Filled circles become much darker.
        if top['score'] < .20:
            answers[str(no)] = None
            continue
        margin = top['score'] - second['score']
        if margin < .055 or second['score'] >= .25:
            answers[str(no)] = None
            issues.append({'question_no': no, 'code': 'AMBIGUOUS_MARK', 'message': f'{no}. soruda birden fazla/belirsiz işaret var', 'scores': diagnostics[str(no)]})
        else:
            answers[str(no)] = top['letter']
    return {'answers': answers, 'issues': issues, 'diagnostics': diagnostics}


def page_fingerprint(warped: np.ndarray) -> str:
    small = cv2.resize(cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY), (160, 110))
    _, bw = cv2.threshold(small, 180, 255, cv2.THRESH_BINARY)
    return sha256(bw.tobytes()).hexdigest()


def full_page_fingerprint(image: np.ndarray) -> str:
    """Stable-enough fingerprint for non-OMR question/support pages."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (180, 255))
    _, bw = cv2.threshold(small, 195, 255, cv2.THRESH_BINARY)
    return sha256(bw.tobytes()).hexdigest()


def analyze_page(image: np.ndarray, metadata: dict) -> dict:
    # QR decoding and OMR registration orientation are independent concerns.
    # Some QR payload patterns are decoded by OpenCV only after a 90/180/270°
    # retry. Using that QR-oriented frame directly made registration detection
    # depend on the QR pattern. Find the OMR frame independently across all
    # four rotations so the same paper is stable for every token/booklet.
    qr, _ = decode_qr(image)
    parsed = parse_qr_payload(qr)
    oriented = image
    marks = None
    for _ in range(4):
        marks = find_registration_marks(oriented)
        if marks is not None:
            break
        oriented = cv2.rotate(oriented, cv2.ROTATE_90_CLOCKWISE)
    if marks is None:
        return {'kind': 'skip', 'reason': 'OMR kayıt işaretleri bulunamadı', 'qr': parsed}
    warped = warp_omr(oriented, marks)
    read = read_bubbles(warped, metadata)
    return {
        'kind': 'omr', 'qr': parsed, 'answers': read['answers'], 'issues': read['issues'],
        'diagnostics': read['diagnostics'], 'fingerprint': page_fingerprint(warped), 'warped': warped,
    }


def jpeg_bytes(image: np.ndarray, quality: int = 86) -> bytes:
    ok, buf = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ScanError('Önizleme JPEG üretilemedi')
    return bytes(buf)


def diagnostic_summary(diagnostics: dict, answers: dict | None = None) -> list[dict]:
    """Convert raw bubble darkness scores into a review-friendly confidence summary.

    This is deliberately derived from the persisted diagnostics so reviewers can
    understand *why* a page was routed to manual inspection without rerunning OCR.
    """
    answers = answers or {}
    rows: list[dict] = []
    for raw_no, raw_scores in (diagnostics or {}).items():
        try:
            no = int(raw_no)
        except Exception:
            continue
        scores = {str(k).upper(): float(v) for k, v in (raw_scores or {}).items()}
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_letter, top_score = ranked[0] if ranked else (None, 0.0)
        second_letter, second_score = ranked[1] if len(ranked) > 1 else (None, 0.0)
        margin = max(0.0, top_score - second_score)
        detected = answers.get(str(no))
        if top_score < .20:
            state = "blank"
            confidence = min(1.0, max(0.0, (.20 - top_score) / .20))
        elif detected:
            state = "marked"
            confidence = min(1.0, max(0.0, (margin - .055) / .18 + .55))
        else:
            state = "ambiguous"
            confidence = min(.49, max(0.0, margin / .055 * .49))
        rows.append({
            "question_no": no,
            "detected_answer": detected,
            "suggested_answer": top_letter if top_score >= .20 else None,
            "state": state,
            "confidence": round(float(confidence), 4),
            "margin": round(float(margin), 4),
            "top_candidates": [
                {"letter": letter, "score": round(float(score), 4)}
                for letter, score in ranked[:3]
            ],
        })
    return sorted(rows, key=lambda x: x["question_no"])


def annotated_review_preview(warped: np.ndarray, metadata: dict, answers: dict, diagnostics: dict, issues: list[dict] | None = None) -> np.ndarray:
    """Draw reviewer hints over the normalized OMR region.

    Green rings are confidently detected answers, amber rings are candidate marks
    for ambiguous questions, and gray rings are unselected bubbles. The original
    warped image remains the source of truth; this image is only a visual aid.
    """
    canvas = warped.copy()
    layout = metadata.get("omr_layout") or {}
    issue_qs = {
        int(x.get("question_no")) for x in (issues or [])
        if x.get("code") == "AMBIGUOUS_MARK" and x.get("question_no") is not None
    }
    candidate_map: dict[int, set[str]] = {}
    for row in diagnostic_summary(diagnostics, answers):
        if row["question_no"] in issue_qs or row["state"] == "ambiguous":
            candidate_map[row["question_no"]] = {x["letter"] for x in row["top_candidates"][:2]}

    seen: set[int] = set()
    for bubble in layout.get("bubbles", []):
        no = int(bubble["display_no"])
        letter = str(bubble["letter"]).upper()
        x = int(float(bubble["x"]) * (CANON_W - 1))
        y = int(float(bubble["y"]) * (CANON_H - 1))
        selected = (answers or {}).get(str(no)) == letter
        ambiguous_candidate = letter in candidate_map.get(no, set())
        if selected:
            color, thickness, radius = (35, 145, 65), 3, 16
        elif ambiguous_candidate:
            color, thickness, radius = (0, 145, 255), 3, 17
        else:
            color, thickness, radius = (155, 155, 155), 1, 14
        cv2.circle(canvas, (x, y), radius, color, thickness, lineType=cv2.LINE_AA)
        if no not in seen:
            label_color = (0, 110, 220) if no in issue_qs else (80, 80, 80)
            cv2.putText(canvas, f"S{no}", (max(2, x - 45), max(16, y + 5)), cv2.FONT_HERSHEY_SIMPLEX, .42, label_color, 1, cv2.LINE_AA)
            seen.add(no)
    return canvas
