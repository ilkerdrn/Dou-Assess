from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import fitz
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app import models as m
from app.services.paper import build_exam_pdf
from app.services.scan import CANON_W, CANON_H, find_registration_marks, _order_points


def load_exam(db, exam_id: int):
    stmt = select(m.Exam).options(
        selectinload(m.Exam.learning_outcomes),
        selectinload(m.Exam.program_outcomes),
        selectinload(m.Exam.questions).selectinload(m.Question.learning_outcome),
        selectinload(m.Exam.questions).selectinload(m.Question.learning_outcomes),
        selectinload(m.Exam.exam_students).selectinload(m.ExamStudent.student),
    ).where(m.Exam.id == exam_id)
    exam = db.scalar(stmt)
    if not exam:
        raise SystemExit(f"Exam not found: {exam_id}")
    return exam


def _student_for_exam(exam, student_no: str):
    for es in exam.exam_students:
        if es.student and str(es.student.student_no) == str(student_no):
            return es.student
    raise SystemExit(f"Student is not assigned to exam: {student_no}")


def _render_page(doc: fitz.Document, page_index: int, dpi: int = 220) -> np.ndarray:
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _find_omr_page(doc: fitz.Document) -> tuple[int, np.ndarray, np.ndarray]:
    # Embedded forms normally live on the first page, while separate OMR forms live
    # on a later page. Detect the four registration marks instead of assuming a page.
    for page_index in range(len(doc)):
        image = _render_page(doc, page_index)
        marks = find_registration_marks(image)
        if marks is not None:
            return page_index, image, _order_points(marks)
    raise SystemExit("OMR registration marks were not found in generated paper")


def _canonical_to_image(points: list[tuple[float, float]], ordered_marks: np.ndarray) -> list[tuple[int, int]]:
    canonical = np.array(
        [[0, 0], [CANON_W - 1, 0], [CANON_W - 1, CANON_H - 1], [0, CANON_H - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(canonical, ordered_marks.astype(np.float32))
    src = np.array([[[float(x), float(y)]] for x, y in points], dtype=np.float32)
    dst = cv2.perspectiveTransform(src, matrix).reshape(-1, 2)
    return [(int(round(x)), int(round(y))) for x, y in dst]


def _mark_answer(image: np.ndarray, ordered_marks: np.ndarray, bubble: dict, radius: int = 13) -> None:
    cx = float(bubble["x"]) * (CANON_W - 1)
    cy = float(bubble["y"]) * (CANON_H - 1)
    (x, y), = _canonical_to_image([(cx, cy)], ordered_marks)
    # Scale radius with the registered OMR area so camera/ADF-sized renders stay valid.
    span = max(1.0, float(np.linalg.norm(ordered_marks[1] - ordered_marks[0])))
    rr = max(6, int(round(radius * span / CANON_W)))
    cv2.circle(image, (x, y), rr, (0, 0, 0), thickness=-1, lineType=cv2.LINE_AA)


def _answer_bubbles(layout: dict) -> dict[tuple[int, str], dict]:
    return {
        (int(b["display_no"]), str(b["letter"]).upper()): b
        for b in (layout or {}).get("bubbles", [])
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a filled OMR fixture for DOU Assess OMR v2")
    ap.add_argument("--exam-id", type=int, required=True)
    ap.add_argument("--student-no", required=True)
    ap.add_argument("--booklet", default="A", choices=list("ABCD"))
    ap.add_argument("--output", required=True)
    ap.add_argument("--ambiguous", type=int, default=0, help="Display question number to double-mark")
    ap.add_argument("--adf", action="store_true", help="Output an ADF-like multi-page PDF")
    args = ap.parse_args()

    with SessionLocal() as db:
        exam = load_exam(db, args.exam_id)
        student = _student_for_exam(exam, args.student_no)
        try:
            pdf, meta = build_exam_pdf(exam, args.booklet, student=student)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    layout = meta.get("omr_layout") or {}
    bubbles = _answer_bubbles(layout)
    if not bubbles:
        raise SystemExit("Exam paper has no MCQ bubbles")

    doc = fitz.open(stream=pdf, filetype="pdf")
    page_index, image, ordered_marks = _find_omr_page(doc)

    for raw_no, raw_answer in (meta.get("answer_key") or {}).items():
        if not raw_answer:
            continue
        key = (int(raw_no), str(raw_answer).upper())
        bubble = bubbles.get(key)
        if not bubble:
            raise SystemExit(f"Bubble not found for question {raw_no} / {raw_answer}")
        _mark_answer(image, ordered_marks, bubble)

    if args.ambiguous:
        no = int(args.ambiguous)
        expected = str((meta.get("answer_key") or {}).get(str(no)) or "A").upper()
        options = sorted(letter for qno, letter in bubbles if qno == no and letter != expected)
        if not options:
            raise SystemExit(f"No alternate bubble for ambiguous question {no}")
        _mark_answer(image, ordered_marks, bubbles[(no, options[0])])

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    ok, png = cv2.imencode(".png", image)
    if not ok:
        raise SystemExit("PNG encode failed")

    if args.adf:
        adf = fitz.open()
        for i in range(len(doc)):
            if i == page_index:
                src_page = doc[i]
                page = adf.new_page(width=src_page.rect.width, height=src_page.rect.height)
                page.insert_image(page.rect, stream=png.tobytes())
            else:
                adf.insert_pdf(doc, from_page=i, to_page=i)
        out.write_bytes(adf.tobytes())
    else:
        out.write_bytes(png.tobytes())
    print(str(out))


if __name__ == "__main__":
    main()
