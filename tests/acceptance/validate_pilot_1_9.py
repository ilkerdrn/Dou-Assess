from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook
from PIL import Image, ImageDraw
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TMP = Path(tempfile.mkdtemp(prefix="dou_assess_uat_1_9_"))
DB = TMP / "uat.db"
OUTPUT = Path(os.environ.get("DOU_UAT_OUTPUT", str(TMP / "outputs"))).resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{DB.as_posix()}"
os.environ["APP_ENV"] = "pilot"
os.environ["EVIDENCE_STORAGE_PATH"] = str(TMP / "evidence")
os.environ["SCAN_STORAGE_PATH"] = str(TMP / "scans")
os.environ["AUTH_REQUIRED"] = "false"

from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app

Base.metadata.create_all(engine)
client = TestClient(app)

checks: list[dict] = []
artifacts: dict[str, str] = {}


def check(name: str, ok: bool, detail=""):
    row = {"name": name, "ok": bool(ok), "detail": detail}
    checks.append(row)
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def req(method: str, path: str, *, json_data=None, headers=None, files=None, data=None, expected=(200, 201)):
    r = client.request(method, path, json=json_data, headers=headers, files=files, data=data)
    if r.status_code not in expected:
        raise AssertionError(f"{method} {path} -> {r.status_code}: {r.text}")
    return r


def post(path: str, data: dict, headers=None):
    return req("POST", path, json_data=data, headers=headers).json()


def save_bytes(name: str, raw: bytes) -> Path:
    path = OUTPUT / name
    path.write_bytes(raw)
    artifacts[name] = str(path)
    return path


def make_diagram_data_url() -> str:
    im = Image.new("RGB", (720, 240), "white")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((25, 70, 210, 170), radius=16, outline="black", width=4)
    d.rounded_rectangle((510, 70, 695, 170), radius=16, outline="black", width=4)
    d.line((210, 120, 510, 120), fill="black", width=5)
    d.polygon([(500, 110), (510, 120), (500, 130)], fill="black")
    d.text((65, 105), "CLIENT", fill="black")
    d.text((555, 105), "SERVER", fill="black")
    d.text((305, 82), "HTTP REQUEST", fill="black")
    buf = BytesIO(); im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# 1) Ana ekran + pilot auth + rol/yetki
root = client.get("/")
check("1.1 Ana uygulama sayfası", root.status_code == 200 and b"DOU" in root.content, f"HTTP {root.status_code}")
me = req("GET", "/api/auth/me").json()
check("1.2 Pilot admin oturumu", "admin" in (me.get("role_names") or []), me.get("email"))

program = post("/api/programs", {
    "code": "UAT-BP", "name": "Bilgisayar Programcılığı · UAT", "faculty": "Meslek Yüksekokulu", "department": "Bilgisayar Teknolojileri"
})
course = post("/api/courses", {
    "program_id": program["id"], "code": "UAT-PY101", "name": "Python Programlama · Tam Pilot",
    "academic_year": "2026-2027", "term": "Pilot Demo", "instructor_email": "uat-ogretim@local",
    "instructor_name": "UAT Öğretim Elemanı", "pass_threshold_percent": 60
})
user = post("/api/users", {"email": "uat-ogretim@local", "display_name": "UAT Öğretim Elemanı", "auth_source": "pilot", "is_active": True})
role = post(f"/api/users/{user['id']}/roles", {"role": "instructor", "course_id": course["id"]})
instructor_headers = {"X-DOU-Pilot-User": "uat-ogretim@local"}
instructor_me = req("GET", "/api/auth/me", headers=instructor_headers).json()
check("1.3 Öğretim elemanı rolü", "instructor" in instructor_me.get("role_names", []), str(instructor_me.get("roles")))
check("1.4 Öğretim elemanı ders erişimi", req("GET", f"/api/courses?program_id={program['id']}", headers=instructor_headers).status_code == 200)
forbidden = client.post("/api/accreditation/profiles", headers=instructor_headers, json={
    "code": "NOPE", "name": "Yetkisiz", "version": "1", "required_general_evidence_kinds": []
})
check("1.5 Admin/quality yetki sınırı", forbidden.status_code == 403, f"HTTP {forbidden.status_code}")

# 2) Ders + 30 öğrenci + ÖÇ/PÇ
los = []
for code, desc, target in [
    ("Ö1", "Python temel söz dizimi ve veri türlerini uygular", 70),
    ("Ö2", "Koşul ve döngülerle algoritma geliştirir", 70),
    ("Ö3", "Fonksiyon ve koleksiyonları problem çözmede kullanır", 70),
    ("Ö4", "Program çıktısını analiz eder, hata ayıklar ve iyileştirir", 70),
]:
    los.append(post(f"/api/courses/{course['id']}/learning-outcomes", {"code": code, "description": desc, "target_percent": target}))
pos = []
for code, desc in [
    ("PÇ1", "Temel bilişim kavramlarını uygular"),
    ("PÇ2", "Algoritmik problem çözme becerisi gösterir"),
    ("PÇ3", "Yazılım geliştirme araçlarını etkin kullanır"),
    ("PÇ4", "Teknik çıktıları analiz eder ve iyileştirir"),
]:
    pos.append(post(f"/api/programs/{program['id']}/program-outcomes", {"academic_year": "2026-2027", "code": code, "description": desc}))
for i, lo in enumerate(los):
    post("/api/outcome-mappings", {"learning_outcome_id": lo["id"], "program_outcome_id": pos[i]["id"], "contribution": 5})
    if i > 0:
        post("/api/outcome-mappings", {"learning_outcome_id": lo["id"], "program_outcome_id": pos[i-1]["id"], "contribution": 2})
students = []
for i in range(1, 31):
    students.append(post("/api/students", {
        "program_id": program["id"], "student_no": f"2600{i:05d}", "full_name": f"Pilot Öğrenci {i:02d}", "class_name": "1. Sınıf"
    }))
req("POST", f"/api/courses/{course['id']}/enrollments/bulk", json_data={"student_ids": [s["id"] for s in students]})
outcomes = req("GET", f"/api/courses/{course['id']}/outcomes").json()
check("2.1 Öğrenci kayıtları", len(req("GET", f"/api/courses/{course['id']}/enrollments").json()) == 30, "30 öğrenci")
check("2.2 ÖÇ/PÇ yapısı", len(outcomes.get("learning_outcomes", [])) == 4 and len(outcomes.get("program_outcomes", [])) == 4, "4 ÖÇ + 4 PÇ")

# 3) Soru Bankası 2.0
image_data = make_diagram_data_url()
bank = []
bank_specs = [
    ("mcq", "Şemadaki istemci-sunucu iletişiminde HTTP isteğini başlatan taraf hangisidir?", 10, "A", {"A": "İstemci", "B": "Sunucu", "C": "Veritabanı", "D": "Yönlendirici"}, ["Ö1"], "İstemci-Sunucu", "HTTP", "medium", "apply", image_data, None),
    ("mcq", "Python'da tam sayı veri tipi hangisidir?", 10, "A", {"A":"int","B":"str","C":"list","D":"bool"}, ["Ö1"], "Veri Tipleri", "Python Temelleri", "easy", "remember", None, None),
    ("mcq", "Koşullu dallanmada kullanılan anahtar sözcük hangisidir?", 10, "B", {"A":"def","B":"if","C":"import","D":"return"}, ["Ö2"], "Koşullar", "Kontrol Yapıları", "easy", "understand", None, None),
    ("mcq", "Döngüyü erken sonlandıran ifade hangisidir?", 10, "C", {"A":"pass","B":"next","C":"break","D":"stop"}, ["Ö2"], "Döngüler", "Kontrol Yapıları", "medium", "apply", None, None),
    ("mcq", "Fonksiyon tanımlamak için hangi anahtar sözcük kullanılır?", 10, "B", {"A":"func","B":"def","C":"method","D":"function"}, ["Ö3"], "Fonksiyonlar", "Modüler Programlama", "easy", "remember", None, None),
    ("mcq", "Liste sonuna eleman ekleyen metot hangisidir?", 10, "A", {"A":"append","B":"push","C":"addLast","D":"insertEnd"}, ["Ö3"], "Listeler", "Koleksiyonlar", "medium", "apply", None, None),
    ("mcq", "Bir istisnayı yakalamak için hangi yapı kullanılır?", 10, "B", {"A":"if/else","B":"try/except","C":"for/while","D":"def/return"}, ["Ö4"], "Hata Yönetimi", "Debug", "medium", "analyze", None, None),
    ("mcq", "Kodun çalışmasını adım adım inceleme işlemine ne ad verilir?", 10, "B", {"A":"encoding","B":"debugging","C":"deploy","D":"compile"}, ["Ö4"], "Debug", "Debug", "medium", "understand", None, None),
    ("mcq", "range(5) ifadesi kaç yineleme üretir?", 10, "C", {"A":"4","B":"6","C":"5","D":"1"}, ["Ö2"], "Döngüler", "Kontrol Yapıları", "medium", "apply", None, None),
    ("mcq", "Bir listenin eleman sayısını hangi fonksiyon verir?", 10, "D", {"A":"size","B":"countall","C":"items","D":"len"}, ["Ö3"], "Listeler", "Koleksiyonlar", "easy", "understand", None, None),
]
for idx, spec in enumerate(bank_specs, 1):
    qtype, text, pts, correct, choices, codes, topic, unit, difficulty, bloom, img, rubric = spec
    bank.append(post("/api/question-bank", {
        "course_id": course["id"], "question_type": qtype, "text": text, "default_points": pts,
        "correct_answer": correct, "choices": choices, "learning_outcome_codes": codes,
        "tags": ["UAT", "Python", topic], "topic": topic, "unit": unit, "difficulty": difficulty,
        "bloom_level": bloom, "author": "UAT Öğretim Elemanı", "reviewer": "Program Başkanı",
        "image_data": img, "rubric": rubric
    }))
rubric = {"criteria": [
    {"id":"alg", "label":"Algoritma ve yaklaşım", "max_points":25, "outcome_codes":["Ö4"]},
    {"id":"code", "label":"Kodlama doğruluğu", "max_points":20, "outcome_codes":["Ö4"]},
    {"id":"out", "label":"Beklenen çıktı", "max_points":10, "outcome_codes":["Ö4"]},
    {"id":"read", "label":"Okunabilirlik", "max_points":5, "outcome_codes":["Ö4"]},
]}
classic_bank = post("/api/question-bank", {
    "course_id": course["id"], "question_type": "classic", "text": "Hatalı verilen Python kodunu düzeltip çözüm yaklaşımınızı açıklayınız.",
    "default_points": 60, "learning_outcome_codes": ["Ö4"], "tags": ["UAT","Klasik","Rubrik"],
    "topic":"Hata Ayıklama", "unit":"Debug", "difficulty":"hard", "bloom_level":"create",
    "author":"UAT Öğretim Elemanı", "reviewer":"Program Başkanı", "rubric": rubric, "answer_lines": 14, "expected_answer":"Hatalı kod düzeltilir; hata nedeni ve çözüm yaklaşımı açıklanır."
})
bank.append(classic_bank)
bank_rows = req("GET", f"/api/question-bank?course_id={course['id']}").json()
check("3.1 Soru bankası metadata", len(bank_rows) == 11 and any(x.get("image_data") for x in bank_rows) and any(x.get("rubric") for x in bank_rows), "11 soru; görsel + rubrik")

# 4) Vize %40 + A/B/C/D + A4 OMR
vize = post("/api/exams", {
    "course_id": course["id"], "title":"UAT · Vize", "exam_type":"Vize", "exam_date":"2026-11-16", "start_time":"10:00",
    "location":"D-101", "duration_minutes":50, "assessment_weight_percent":40, "booklet_count":4,
    "instructions":"Soruları dikkatle okuyunuz. Optikte tek seçenek işaretleyiniz.",
    "paper_size":"A4", "paper_orientation":"portrait", "omr_mode":"embedded", "duplex_print":False, "sync_students":True
})
for i, b in enumerate(bank[:10], 1):
    post(f"/api/exams/{vize['id']}/questions/from-bank", {"bank_question_id": b["id"], "order_no": i, "points": 10})
ready = req("GET", f"/api/exams/{vize['id']}/readiness").json()
check("4.1 Vize sınav hazırlık kontrolü", ready.get("ready") is True, json.dumps(ready, ensure_ascii=False)[:300])
req("POST", f"/api/exams/{vize['id']}/status", json_data={"status":"ready"})
req("POST", f"/api/exams/{vize['id']}/status", json_data={"status":"grading"})
vize_pdf = req("GET", f"/api/exams/{vize['id']}/paper.pdf?booklet=A").content
save_bytes("01-UAT-Vize-A.pdf", vize_pdf)
vr = PdfReader(BytesIO(vize_pdf))
check("4.2 Vize PDF", len(vr.pages) >= 1, f"{len(vr.pages)} sayfa")
for booklet in "ABCD":
    meta = req("GET", f"/api/exams/{vize['id']}/paper-metadata?booklet={booklet}").json()
    check(f"4.3 Kitapçık {booklet}", meta.get("booklet") == booklet and len(meta.get("answer_key", {})) == 10, meta.get("token"))

# 5) Gerçek OMR: kabul + belirsiz işaret + manuel çözüm
fixture_ok = OUTPUT / "02-OMR-accepted.png"
fixture_review = OUTPUT / "03-OMR-ambiguous.png"
env = os.environ.copy()
subprocess.run([sys.executable, "-m", "app.tools.generate_omr_fixture", "--exam-id", str(vize["id"]), "--student-no", students[0]["student_no"], "--booklet", "A", "--output", str(fixture_ok)], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
subprocess.run([sys.executable, "-m", "app.tools.generate_omr_fixture", "--exam-id", str(vize["id"]), "--student-no", students[1]["student_no"], "--booklet", "A", "--ambiguous", "1", "--output", str(fixture_review)], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
artifacts[fixture_ok.name] = str(fixture_ok); artifacts[fixture_review.name] = str(fixture_review)
with fixture_ok.open("rb") as f:
    scan_ok = req("POST", f"/api/exams/{vize['id']}/scans", files={"file": (fixture_ok.name, f, "image/png")}).json()
check("5.1 OMR otomatik kabul", scan_ok.get("accepted_count") == 1 and scan_ok.get("review_count") == 0, str(scan_ok))
with fixture_review.open("rb") as f:
    scan_review = req("POST", f"/api/exams/{vize['id']}/scans", files={"file": (fixture_review.name, f, "image/png")}).json()
check("5.2 Belirsiz optik incelemeye düşer", scan_review.get("review_count") == 1, str(scan_review))
reviews = req("GET", f"/api/exams/{vize['id']}/scan-reviews").json()
check("5.3 İnceleme kuyruğu", len(reviews) >= 1, str(reviews[:1]))
review = reviews[0]
meta_a = req("GET", f"/api/exams/{vize['id']}/paper-metadata?booklet=A").json()
resolved = req("POST", f"/api/scan-items/{review['scan_item_id']}/resolve", json_data={
    "action":"accept", "student_id": students[1]["id"], "booklet":"A", "answers": meta_a["answer_key"], "note":"UAT manuel doğrulama"
}).json()
check("5.4 Manuel optik çözümü", resolved.get("status") == "accepted", str(resolved))

# Fill deterministic Vize scores for all 30 students (scanned rows are safely updated)
vize_questions = req("GET", f"/api/exams/{vize['id']}").json()["questions"]
vize_exam_students = req("GET", f"/api/exams/{vize['id']}/students").json()
for si, es in enumerate(vize_exam_students):
    items=[]
    for qi, q in enumerate(vize_questions):
        correct = q.get("correct_answer")
        if qi < 6:
            is_correct = (si % 10) < 8
        elif qi < 8:
            is_correct = (si % 10) < 4  # Ö4 intentionally weak
        else:
            is_correct = (si % 10) < 7
        choices = list((q.get("choices") or {}).keys())
        wrong = next((x for x in choices if x != correct), "A")
        items.append({"question_id": q["id"], "answer_text": correct if is_correct else wrong})
    req("POST", f"/api/exams/{vize['id']}/students/{es['id']}/responses", json_data={"responses": items})
req("POST", f"/api/exams/{vize['id']}/approval-request", json_data={"note":"UAT Vize sonuçları kontrol için gönderildi"})
req("POST", f"/api/exams/{vize['id']}/status", json_data={"status":"approved", "note":"UAT onayı"})

# 6) Final %60 + A3 yatay + ayrı optik + rubrik
final_exam = post("/api/exams", {
    "course_id": course["id"], "title":"UAT · Final", "exam_type":"Final", "exam_date":"2027-01-18", "start_time":"11:00",
    "location":"D-102", "duration_minutes":75, "assessment_weight_percent":60, "booklet_count":2,
    "instructions":"Test ve klasik bölümleri cevaplayınız.", "paper_size":"A3", "paper_orientation":"landscape",
    "omr_mode":"separate", "duplex_print":True, "sync_students":True
})
for i, b in enumerate([bank[1], bank[3], bank[5], bank[6]], 1):
    post(f"/api/exams/{final_exam['id']}/questions/from-bank", {"bank_question_id": b["id"], "order_no": i, "points": 10})
post(f"/api/exams/{final_exam['id']}/questions/from-bank", {"bank_question_id": classic_bank["id"], "order_no": 5, "points": 60})
req("POST", f"/api/exams/{final_exam['id']}/status", json_data={"status":"ready"})
req("POST", f"/api/exams/{final_exam['id']}/status", json_data={"status":"grading"})
final_pdf = req("GET", f"/api/exams/{final_exam['id']}/paper.pdf?booklet=A").content
save_bytes("04-UAT-Final-A3-Yatay.pdf", final_pdf)
fr = PdfReader(BytesIO(final_pdf)); fw, fh = float(fr.pages[0].mediabox.width), float(fr.pages[0].mediabox.height)
check("6.1 A3 yatay PDF", fw > fh and 1180 < fw < 1200 and 835 < fh < 850, f"{fw:.2f} x {fh:.2f} pt")
check("6.2 Duplex sayfa çifti", len(fr.pages) % 2 == 0, f"{len(fr.pages)} sayfa")
final_qs = req("GET", f"/api/exams/{final_exam['id']}").json()["questions"]
final_students = req("GET", f"/api/exams/{final_exam['id']}/students").json()
for si, es in enumerate(final_students):
    payload=[]
    for qi, q in enumerate(final_qs):
        if q["question_type"] == "mcq":
            correct = q.get("correct_answer"); choices=list((q.get("choices") or {}).keys()); wrong=next((x for x in choices if x!=correct),"A")
            good = (si % 10) < (8 if qi < 3 else 5)
            payload.append({"question_id":q["id"], "answer_text": correct if good else wrong})
        else:
            # 18 students around 45/60, 12 students around 24/60 to create a real improvement gap.
            if si < 18:
                scores={"alg":20,"code":15,"out":7,"read":3}
            else:
                scores={"alg":10,"code":8,"out":4,"read":2}
            payload.append({"question_id":q["id"], "answer_text":"Rubrikli öğrenci yanıtı", "rubric_scores":scores})
    req("POST", f"/api/exams/{final_exam['id']}/students/{es['id']}/responses", json_data={"responses": payload})
req("POST", f"/api/exams/{final_exam['id']}/approval-request", json_data={"note":"UAT Final sonuçları kontrol için gönderildi"})
req("POST", f"/api/exams/{final_exam['id']}/status", json_data={"status":"approved", "note":"UAT onayı"})

# 7) Analiz + weighted gradebook + psychometrics
vize_an = req("GET", f"/api/exams/{vize['id']}/analytics").json()
final_an = req("GET", f"/api/exams/{final_exam['id']}/analytics").json()
check("7.1 Güvenilirlik metrikleri", "cronbach_alpha" in vize_an.get("reliability", {}) and "kr20" in vize_an.get("reliability", {}), str(vize_an.get("reliability")))
check("7.2 Madde ayırt edicilik", all("discrimination_index" in q and "point_biserial" in q for q in vize_an.get("question_analysis", [])), "Tüm test sorularında")
check("7.3 Çeldirici analizi", all("distractors" in q for q in vize_an.get("question_analysis", []) if q.get("question_type") == "mcq"), "Dağılımlar mevcut")
gradebook = req("GET", f"/api/courses/{course['id']}/gradebook").json()
check("7.4 Vize %40 + Final %60", gradebook.get("weights_valid") is True and gradebook.get("assessment_weight_total") == 100, str(gradebook.get("assessment_weight_total")))
check("7.5 Ağırlıklı ÖÇ/PÇ", bool(gradebook.get("learning_outcomes")) and bool(gradebook.get("program_outcomes")), "weighted outcome summaries")
quality = req("GET", f"/api/quality/courses/{course['id']}/drilldown").json()
check("7.6 Kalite drill-down", quality.get("course", {}).get("id") == course["id"], str(quality.get("course")))
results_xlsx = req("GET", f"/api/exams/{vize['id']}/results.xlsx").content
save_bytes("05-UAT-Vize-Analiz.xlsx", results_xlsx)
rwb=load_workbook(BytesIO(results_xlsx),data_only=True)
headers=[c.value for c in rwb["Soru_Analizi"][1]]
check("7.7 Excel gelişmiş analiz", "Ayırt Edicilik" in headers and "Çeldirici Dağılımı" in headers, str(headers))

# 8) İyileştirme + MEDEK/evidence + MIN/AVG/MAX + package
# Add actions for every observed gap in either exam.
gap_codes = sorted({x["code"] for an in (vize_an, final_an) for x in an.get("learning_outcomes", []) if x.get("status") == "needs_improvement"})
for code in gap_codes:
    post(f"/api/exams/{final_exam['id']}/improvements", {
        "outcome_code": code, "action_text": f"{code} için ek uygulama laboratuvarı, soru revizyonu ve yeniden ölçme planı uygulanacaktır.",
        "owner":"UAT Öğretim Elemanı", "due_date":"2027-03-15"
    })
# Accreditation checks are per exam; cover any Vize gaps too.
for code in [x["code"] for x in vize_an.get("learning_outcomes", []) if x.get("status") == "needs_improvement"]:
    post(f"/api/exams/{vize['id']}/improvements", {
        "outcome_code": code, "action_text": f"{code} için vize sonrası hedefli tekrar ve uygulama çalışması.", "owner":"UAT Öğretim Elemanı", "due_date":"2026-12-15"
    })
profile = post("/api/accreditation/profiles", {
    "code":"MEDEK-UAT", "name":"MEDEK Yerel Pilot Profili", "version":"1.0",
    "required_general_evidence_kinds":["exam_paper"], "required_representative_evidence_kinds":["answer_sheet"],
    "requires_representatives":True, "requires_improvement_for_gaps":True
})
period = post("/api/accreditation/periods", {
    "program_id":program["id"], "profile_id":profile["id"], "academic_year":"2026-2027", "term":"Pilot Demo", "title":"2026-2027 Yerel MEDEK UAT"
})
req("POST", f"/api/accreditation/periods/{period['id']}/sync-exams", json_data={})
req("POST", f"/api/accreditation/periods/{period['id']}/representatives/freeze-all", json_data={})
# General exam paper evidence + representative answer-sheet evidence for both exams.
for exam_obj, pdf_bytes, label in [(vize, vize_pdf, "Vize"), (final_exam, final_pdf, "Final")]:
    rr = client.post(f"/api/exams/{exam_obj['id']}/evidence", data={"kind":"exam_paper","category":"medek","description":f"{label} sınav kağıdı UAT kanıtı"}, files={"file":(f"{label}.pdf", pdf_bytes, "application/pdf")})
    check(f"8.{label}.1 Genel kanıt", rr.status_code == 201, rr.text[:200])
    reps = req("GET", f"/api/exams/{exam_obj['id']}/representatives").json()
    check(f"8.{label}.2 MIN/AVG/MAX", {x.get('slot') for x in reps} == {"MIN","AVG","MAX"}, str(reps))
    for rep in reps:
        im = Image.new("RGB", (640, 360), "white"); d=ImageDraw.Draw(im); d.text((30,30), f"{label} {rep['slot']} - {rep['student_no']}", fill="black")
        b=BytesIO(); im.save(b,format="PNG")
        rr = client.post(f"/api/exams/{exam_obj['id']}/evidence", data={"kind":"answer_sheet","student_id":str(rep["student_id"]),"category":"medek","description":f"{rep['slot']} temsilci cevap kağıdı"}, files={"file":(f"{label}-{rep['slot']}.png", b.getvalue(), "image/png")})
        check(f"8.{label}.3 {rep['slot']} kanıtı", rr.status_code == 201, rr.text[:150])

dash = req("GET", f"/api/accreditation/periods/{period['id']}/dashboard").json()
check("8.1 Akreditasyon dashboard hazır", dash.get("summary", {}).get("ready") is True, json.dumps(dash.get("summary"), ensure_ascii=False))
req("POST", f"/api/accreditation/periods/{period['id']}/status", json_data={"status":"ready"})
accred_xlsx = req("GET", f"/api/accreditation/periods/{period['id']}/report.xlsx").content
save_bytes("06-UAT-MEDEK-Raporu.xlsx", accred_xlsx)
package = req("GET", f"/api/accreditation/periods/{period['id']}/evidence-package").content
package_path = save_bytes("07-UAT-MEDEK-Kanit-Paketi.zip", package)
with zipfile.ZipFile(package_path) as z:
    names=set(z.namelist())
    check("8.2 Kanıt paketi içeriği", "SHA256SUMS.json" in names and "00-Akreditasyon-Degerlendirme-Raporu.xlsx" in names, f"{len(names)} dosya")

# 9) Gradebook + OBS Excel (real external OBS push intentionally excluded)
grade_xlsx = req("GET", f"/api/courses/{course['id']}/gradebook.xlsx").content
obs_xlsx = req("GET", f"/api/courses/{course['id']}/obs-results.xlsx").content
save_bytes("08-UAT-Agirlikli-Not-Defteri.xlsx", grade_xlsx)
save_bytes("09-UAT-OBS-Sonuclari.xlsx", obs_xlsx)
gwb = load_workbook(BytesIO(grade_xlsx), data_only=True)
check("9.1 Not defteri sayfaları", {"Ders_Notlari","Agirlikli_OC","Agirlikli_PC","Ozet"}.issubset(set(gwb.sheetnames)), str(gwb.sheetnames))
owb = load_workbook(BytesIO(obs_xlsx), data_only=True)
check("9.2 OBS Excel üretildi", len(owb.sheetnames) >= 1 and len(obs_xlsx) > 1000, str(owb.sheetnames))

# Final report
summary = {
    "status": "PASS",
    "scope": "DOU Assess Local Pilot UAT 1-9 (production/institution integration step 10 excluded)",
    "program_id": program["id"], "course_id": course["id"], "vize_exam_id": vize["id"], "final_exam_id": final_exam["id"],
    "student_count": 30, "weights": {"Vize":40, "Final":60}, "pass_threshold":60,
    "omr": {"accepted": scan_ok, "manual_review": scan_review},
    "vize_reliability": vize_an.get("reliability"), "final_reliability": final_an.get("reliability"),
    "gap_codes": gap_codes, "accreditation_ready": dash.get("summary", {}).get("ready"),
    "checks_passed": sum(1 for x in checks if x["ok"]), "checks_total": len(checks), "checks": checks,
    "artifacts": artifacts,
}
report_json = OUTPUT / "UAT-1-9-REPORT.json"; report_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"); artifacts[report_json.name]=str(report_json)
lines=["# DOU Assess · Local Pilot UAT 1–9", "", "**Sonuç: PASS**", "", f"- Öğrenci: 30", "- Ders başarı eşiği: %60", "- Vize: %40", "- Final: %60", f"- Kontrol: {summary['checks_passed']}/{summary['checks_total']} PASS", f"- MEDEK/evidence hazır: {summary['accreditation_ready']}", "", "## Kontroller"]
for c in checks:
    lines.append(f"- {'✅' if c['ok'] else '❌'} {c['name']}" + (f" — {c['detail']}" if c.get('detail') else ""))
lines += ["", "## Çıktılar"] + [f"- `{name}`" for name in artifacts]
report_md = OUTPUT / "UAT-1-9-REPORT.md"; report_md.write_text("\n".join(lines), encoding="utf-8"); artifacts[report_md.name]=str(report_md)
print(json.dumps({k:v for k,v in summary.items() if k not in {"checks","omr"}}, ensure_ascii=False, indent=2))
print(f"REPORT={report_md}")
