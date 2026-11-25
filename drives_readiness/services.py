from accounts.models import StudentProfile
from skills_evidence.models import EvidenceClaim, Skill
from .models import DriveApplication, PlacementDrive


def get_student_verified_skill_map(student_profile):
    """
    Returns a dict mapping skill_id -> highest verified_level (1..4)
    from all EvidenceClaims where status == VERIFIED.
    """
    verified_claims = EvidenceClaim.objects.filter(
        student=student_profile,
        status=EvidenceClaim.STATUS_VERIFIED,
        skill__isnull=False,
        verified_level__isnull=False,
    ).select_related("skill")

    skill_levels = {}
    for claim in verified_claims:
        sid = claim.skill_id
        lvl = int(claim.verified_level)
        if sid not in skill_levels or lvl > skill_levels[sid]:
            skill_levels[sid] = lvl
    return skill_levels


def get_student_dimension_scores(student_profile):
    """
    Computes percentage readiness across the 4 skill dimensions
    (Technical, Aptitude, Communication, Project Depth) from verified claims.
    """
    verified_claims = EvidenceClaim.objects.filter(
        student=student_profile,
        status=EvidenceClaim.STATUS_VERIFIED,
        skill__isnull=False,
        verified_level__isnull=False,
    ).select_related("skill")

    # Best verified level per canonical skill
    best_by_skill = {}
    for claim in verified_claims:
        sid = claim.skill_id
        lvl = int(claim.verified_level)
        if sid not in best_by_skill or lvl > best_by_skill[sid][1]:
            best_by_skill[sid] = (claim.skill.dimension, lvl)

    buckets = {
        Skill.DIMENSION_TECHNICAL: [],
        Skill.DIMENSION_APTITUDE: [],
        Skill.DIMENSION_COMMUNICATION: [],
        Skill.DIMENSION_PROJECT_DEPTH: [],
    }
    for dim, lvl in best_by_skill.values():
        if dim in buckets:
            buckets[dim].append((lvl / 4.0) * 100.0)

    summary = {}
    for dim, vals in buckets.items():
        summary[dim] = round(sum(vals) / len(vals)) if vals else 0
    return summary


def evaluate_eligibility(student_profile, drive):
    """
    Strictly checks formal academic eligibility criteria.
    Returns (is_eligible: bool, reason: str).
    """
    reasons = []

    if student_profile.cgpa < drive.min_cgpa:
        reasons.append(f"CGPA {student_profile.cgpa} < required {drive.min_cgpa}")

    if student_profile.backlogs > drive.max_backlogs:
        reasons.append(f"Backlogs {student_profile.backlogs} > max {drive.max_backlogs}")

    if drive.allowed_branches.strip():
        allowed = [b.strip().upper() for b in drive.allowed_branches.split(",") if b.strip()]
        student_branch = (student_profile.branch or "").strip().upper()
        if not student_branch or student_branch not in allowed:
            reasons.append(f"Branch '{student_profile.branch or 'Unset'}' not in {drive.allowed_branches}")

    if drive.graduation_year:
        if student_profile.graduation_year != drive.graduation_year:
            reasons.append(
                f"Grad year {student_profile.graduation_year or 'Unset'} != {drive.graduation_year}"
            )

    if reasons:
        return False, "; ".join(reasons)
    return True, "Meets all academic eligibility criteria"


def evaluate_readiness(student_profile, drive, skill_map=None):
    """
    Computes weighted readiness score (0..100) and itemized per-skill gap summary
    solely from faculty-verified claims.
    """
    if skill_map is None:
        skill_map = get_student_verified_skill_map(student_profile)

    requirements = list(drive.skill_requirements.select_related("skill").all())

    if not requirements:
        if not skill_map:
            return 0, "No verified skill claims yet"
        avg_ratio = sum(min(lvl / 4.0, 1.0) for lvl in skill_map.values()) / len(skill_map)
        return round(avg_ratio * 100), "General readiness based on verified portfolio skills"

    total_weight = 0
    weighted_score = 0.0
    gap_notes = []

    for req in requirements:
        weight = max(int(req.weight or 1), 1)
        req_lvl = max(int(req.min_level or 1), 1)
        actual_lvl = skill_map.get(req.skill_id, 0)

        ratio = min(actual_lvl / req_lvl, 1.0)
        weighted_score += ratio * weight
        total_weight += weight

        if actual_lvl >= req_lvl:
            gap_notes.append(f"{req.skill.name}: Lvl {actual_lvl}/{req_lvl} (Met)")
        elif actual_lvl == 0:
            gap_notes.append(f"{req.skill.name}: Lvl 0/{req_lvl} (Missing)")
        else:
            gap_notes.append(f"{req.skill.name}: Lvl {actual_lvl}/{req_lvl} (-{req_lvl - actual_lvl} lvl)")

    score = round((weighted_score / total_weight) * 100) if total_weight > 0 else 0
    return score, " | ".join(gap_notes)


def sync_student_drive_evaluations(student_profile):
    """
    Recomputes live eligibility and readiness for a single student across all drives.
    Preserves locked applied_* snapshot columns on already-submitted applications.
    """
    skill_map = get_student_verified_skill_map(student_profile)
    drives = PlacementDrive.objects.prefetch_related("skill_requirements__skill").all()

    for drive in drives:
        is_elig, elig_reason = evaluate_eligibility(student_profile, drive)
        score, gap_text = evaluate_readiness(student_profile, drive, skill_map=skill_map)

        DriveApplication.objects.update_or_create(
            student=student_profile,
            drive=drive,
            defaults={
                "is_eligible": is_elig,
                "eligibility_reason": elig_reason,
                "readiness_score": score,
                "gap_summary": gap_text,
            },
        )


def sync_drive_evaluations(drive):
    """
    Recomputes live eligibility and readiness for all students against a single drive
    whenever the drive or its skill requirements are created or modified.
    """
    students = StudentProfile.objects.select_related("user").all()
    for student in students:
        is_elig, elig_reason = evaluate_eligibility(student, drive)
        score, gap_text = evaluate_readiness(student, drive)

        DriveApplication.objects.update_or_create(
            student=student,
            drive=drive,
            defaults={
                "is_eligible": is_elig,
                "eligibility_reason": elig_reason,
                "readiness_score": score,
                "gap_summary": gap_text,
            },
        )