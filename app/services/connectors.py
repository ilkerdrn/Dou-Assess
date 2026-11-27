"""Canonical academic data model + connector interface.

Every OBS/SIS integration only has to translate its own responses into these records; the upsert
into DOU Assess' tables (`sync_canonical`) is written once and is identical for every institution.
Adding a second university means writing one new `AcademicConnector`, not touching the sync logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m


@dataclass
class CanonStudent:
    student_no: str
    full_name: str = ""
    external_id: str = ""


@dataclass
class CanonCourse:
    code: str
    name: str
    external_id: str
    program_external_id: str
    program_name: str
    faculty: str = ""
    department: str = ""
    program_code: str = ""
    students: list[CanonStudent] = field(default_factory=list)


@dataclass
class CanonPeriod:
    academic_year: str
    term: str


@dataclass
class CanonTeacher:
    email: str
    display_name: str


class AcademicConnector(Protocol):
    """Implement these three methods for a new institution's OBS."""
    source: str  # stored in external_source ("proliz", "sis-x", ...)

    def resolve_period(self, period_ref: str) -> CanonPeriod: ...
    def teacher_courses(self, teacher_ref: str, period_ref: str) -> list[CanonCourse]: ...  # students included


def sync_canonical(db: Session, connector: AcademicConnector, teacher: CanonTeacher, teacher_ref: str, period_ref: str) -> dict:
    stats = {"courses": 0, "students": 0, "enrollments": 0}
    period = connector.resolve_period(period_ref)
    src = connector.source
    for cc in connector.teacher_courses(teacher_ref, period_ref):
        if not cc.program_external_id or not cc.program_name:
            continue
        program = db.scalar(select(m.Program).where(m.Program.external_source == src, m.Program.external_id == cc.program_external_id))
        if not program and cc.program_code:
            program = db.scalar(select(m.Program).where(m.Program.code == cc.program_code))
        if not program:
            program = m.Program(code=cc.program_code or f"{src.upper()[:4]}-{cc.program_external_id}", name=cc.program_name, faculty=cc.faculty, department=cc.department,
                                external_source=src, external_id=cc.program_external_id)
            db.add(program); db.flush()
        elif not program.external_id:
            program.external_source = src; program.external_id = cc.program_external_id
        course = db.scalar(select(m.Course).where(m.Course.program_id == program.id, m.Course.code == cc.code, m.Course.academic_year == period.academic_year, m.Course.term == period.term))
        if not course:
            course = m.Course(program_id=program.id, code=cc.code, name=cc.name or cc.code, academic_year=period.academic_year, term=period.term,
                              instructor_email=teacher.email, instructor_name=teacher.display_name, external_source=src, external_id=cc.external_id)
            db.add(course); db.flush(); stats["courses"] += 1
        else:
            course.instructor_email = teacher.email; course.instructor_name = teacher.display_name
            if not course.external_id:
                course.external_source = src; course.external_id = cc.external_id
        for cs in cc.students:
            if not cs.student_no:
                continue
            student = db.scalar(select(m.Student).where(m.Student.student_no == cs.student_no))
            if not student:
                student = m.Student(program_id=program.id, student_no=cs.student_no, full_name=cs.full_name or cs.student_no, external_source=src, external_id=cs.external_id or cs.student_no)
                db.add(student); db.flush(); stats["students"] += 1
            if not db.scalar(select(m.Enrollment).where(m.Enrollment.course_id == course.id, m.Enrollment.student_id == student.id)):
                db.add(m.Enrollment(course_id=course.id, student_id=student.id)); stats["enrollments"] += 1
    return stats
