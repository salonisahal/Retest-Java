"""Pure grade-letter calculation (no I/O) shared by the grade service and the seed script."""

_GRADE_BANDS: tuple[tuple[float, str], ...] = (
    (90.0, "A+"),
    (80.0, "A"),
    (70.0, "B"),
    (60.0, "C"),
    (50.0, "D"),
)


def calculate_grade_letter(marks: float, max_marks: float) -> str:
    """Map ``marks`` out of ``max_marks`` to a letter: A+ >=90%, A >=80, B >=70, C >=60, D >=50, else F."""
    if max_marks <= 0:
        raise ValueError("max_marks must be greater than 0")
    # Multiply before dividing and round away binary-float noise so exact boundaries (e.g. 9/10) land correctly.
    percentage = round(marks * 100.0 / max_marks, 9)
    for threshold, letter in _GRADE_BANDS:
        if percentage >= threshold:
            return letter
    return "F"
