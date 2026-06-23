import csv
from pathlib import Path

import numpy as np


def compute_workload_metrics(course_codes: list[str]) -> dict:
    selected = {code.upper() for code in course_codes}
    total_credits = _selected_total_credits(selected)
    workload_distribution = _load_peer_workload_distribution()
    workload_tier, workload_percentile = _workload_from_distribution(
        total_credits,
        workload_distribution,
    )

    return {
        "total_credits": total_credits,
        "workload_tier": workload_tier,
        "workload_percentile": workload_percentile,
        "peer_schedule_count": len(workload_distribution),
    }


def _selected_total_credits(course_codes: set[str]) -> float:
    if not course_codes:
        return 0.0

    credits_by_code = _load_catalog_credits_by_code()
    return round(sum(credits_by_code.get(code, 0.0) for code in course_codes), 2)


def _load_catalog_credits_by_code() -> dict[str, float]:
    path = Path(__file__).resolve().parents[1] / "data" / "courses_prepped.csv"
    if not path.exists():
        return {}

    out: dict[str, float] = {}
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("course_code") or "").strip().upper()
            try:
                credits = float(row.get("credits") or 0)
            except ValueError:
                credits = 0.0
            if code and credits > 0:
                out[code] = credits
    return out


def _load_peer_workload_distribution() -> list[float]:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    course_path = data_dir / "courses.csv"
    enrollment_path = data_dir / "enrollment_mapped.csv"
    if not course_path.exists() or not enrollment_path.exists():
        return []

    credits_by_course_id: dict[str, float] = {}
    with course_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            course_id = (row.get("course_id") or "").strip()
            try:
                credits = float(row.get("credits") or 0)
            except ValueError:
                credits = 0.0
            if course_id and credits > 0:
                credits_by_course_id[course_id] = credits

    totals_by_student: dict[str, float] = {}
    with enrollment_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            student_id = (row.get("student_id") or "").strip()
            course_id = (row.get("course_id") or "").strip()
            credits = credits_by_course_id.get(course_id)
            if not student_id or credits is None:
                continue
            totals_by_student[student_id] = totals_by_student.get(student_id, 0.0) + credits

    return [total for total in totals_by_student.values() if total > 0]


def _workload_from_distribution(total_credits: float, distribution: list[float]) -> tuple[str, float]:
    if not distribution:
        return "unknown", 0.0

    q1, q2, q3 = np.percentile(distribution, [25, 50, 75])
    percentile = sum(1 for total in distribution if total <= total_credits) / len(distribution)

    if total_credits <= q1:
        tier = "light"
    elif total_credits <= q2:
        tier = "moderate"
    elif total_credits <= q3:
        tier = "full"
    else:
        tier = "heavy"

    return tier, round(percentile, 4)
