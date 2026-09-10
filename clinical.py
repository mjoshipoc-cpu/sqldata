"""
Clinical Module registry - patient-level clinical record resources (problems /
allergies), as opposed to the Diagnostic Module's order/result resources:
Condition, AllergyIntolerance.

Pure stdlib - no flask, no fhir.resources.
"""
from __future__ import annotations

from fhirpipeline.invariants.condition import CONDITION_INVARIANTS
from fhirpipeline.invariants.allergyintolerance import ALLERGYINTOLERANCE_INVARIANTS
from fhirpipeline.registry.base import ResourceSpec, COMMON_SEARCH


# ---------------------------------------------------------------------------
# duplicate-key functions (pure - no DB, no flask)
# ---------------------------------------------------------------------------
def condition_duplicate_key(resource: dict) -> dict | None:
    """
    Business key for Condition: same subject + same code + same onset.
    Returns None when there isn't enough to form a key (caller then falls
    back to id-only dedup).
    """
    subject_ref = (resource.get("subject") or {}).get("reference")
    codings = (resource.get("code") or {}).get("coding") or []
    if not subject_ref or not codings:
        return None

    coding = codings[0]
    code = coding.get("code")
    if not code:
        return None
    system = coding.get("system")

    onset = (resource.get("onsetDateTime")
             or (resource.get("onsetPeriod") or {}).get("start"))
    if not onset:
        return None

    query: dict = {
        "DeletedFlag": 0,
        "ResourceData.subject.reference": subject_ref,
        "ResourceData.code.coding.code": code,
        "$or": [
            {"ResourceData.onsetDateTime": onset},
            {"ResourceData.onsetPeriod.start": onset},
        ],
    }
    if system:
        query["ResourceData.code.coding.system"] = system
    return query


def allergyintolerance_duplicate_key(resource: dict) -> dict | None:
    """
    Business key for AllergyIntolerance: same patient + same code + same
    recordedDate. Returns None when there isn't enough to form a key (caller
    then falls back to id-only dedup).
    """
    patient_ref = (resource.get("patient") or {}).get("reference")
    codings = (resource.get("code") or {}).get("coding") or []
    if not patient_ref or not codings:
        return None

    coding = codings[0]
    code = coding.get("code")
    if not code:
        return None
    system = coding.get("system")

    recorded = resource.get("recordedDate")
    if not recorded:
        return None

    query: dict = {
        "DeletedFlag": 0,
        "ResourceData.patient.reference": patient_ref,
        "ResourceData.code.coding.code": code,
        "ResourceData.recordedDate": recorded,
    }
    if system:
        query["ResourceData.code.coding.system"] = system
    return query


# ---------------------------------------------------------------------------
# value sets
# ---------------------------------------------------------------------------
# Condition.clinicalStatus - required binding (condition-clinical)
# https://hl7.org/fhir/R4B/valueset-condition-clinical.html
_CONDITION_CLINICAL_STATUS = {
    "active", "recurrence", "relapse", "inactive", "remission", "resolved",
}
# Condition.verificationStatus - required binding (condition-ver-status)
# https://hl7.org/fhir/R4B/valueset-condition-ver-status.html
_CONDITION_VERIFICATION_STATUS = {
    "unconfirmed", "provisional", "differential", "confirmed", "refuted",
    "entered-in-error",
}
# Condition.category - preferred binding (condition-category)
# https://hl7.org/fhir/R4B/valueset-condition-category.html
_CONDITION_CATEGORY = {"problem-list-item", "encounter-diagnosis"}
# AllergyIntolerance.clinicalStatus - required binding (allergyintolerance-clinical)
# https://hl7.org/fhir/R4B/valueset-allergyintolerance-clinical.html
_ALLERGYINTOLERANCE_CLINICAL_STATUS = {"active", "inactive", "resolved"}
# AllergyIntolerance.verificationStatus - required binding (allergyintolerance-verification)
# https://hl7.org/fhir/R4B/valueset-allergyintolerance-verification.html
_ALLERGYINTOLERANCE_VERIFICATION_STATUS = {
    "unconfirmed", "presumed", "confirmed", "refuted", "entered-in-error",
}
# AllergyIntolerance.type - required binding (allergy-intolerance-type)
_ALLERGYINTOLERANCE_TYPE = {"allergy", "intolerance"}
# AllergyIntolerance.category - required binding (allergy-intolerance-category)
_ALLERGYINTOLERANCE_CATEGORY = {"food", "medication", "environment", "biologic"}
# AllergyIntolerance.criticality - required binding (allergy-intolerance-criticality)
_ALLERGYINTOLERANCE_CRITICALITY = {"low", "high", "unable-to-assess"}

# AllergyIntolerance keys its person-reference on `patient`, not `subject`.
_ALLERGYINTOLERANCE_SEARCH = {
    "_id": "ResourceId",
    "identifier": "ResourceData.identifier.value",
    "clinical-status": "ResourceData.clinicalStatus.coding.code",
    "subject": "ResourceData.patient.reference",
    "patient": "ResourceData.patient.reference",
    "code": "ResourceData.code.coding.code",
}


# ---------------------------------------------------------------------------
# the registry - Clinical Module
# ---------------------------------------------------------------------------
CLINICAL_REGISTRY: dict[str, ResourceSpec] = {
    # https://hl7.org/fhir/R4B/condition.html
    "Condition": ResourceSpec(
        resource_type="Condition",
        collection="Condition",
        # spec min=1: Condition.subject (1..1). clinicalStatus / verificationStatus
        # / code are 0..1 in R4B, enforced conditionally via con-3/con-4/con-5 and
        # value-set bindings below rather than as hard-required elements.
        required_fields=["subject"],
        value_sets={
            # clinicalStatus / verificationStatus - required bindings, checked
            # only when sent (both are 0..1 elements)
            "clinicalStatus.coding.code": _CONDITION_CLINICAL_STATUS,
            "verificationStatus.coding.code": _CONDITION_VERIFICATION_STATUS,
            # category - preferred binding, checked only when sent
            "category.coding.code": _CONDITION_CATEGORY,
        },
        # con-3  clinicalStatus SHALL NOT be present if verificationStatus is
        #        entered-in-error
        # con-4  abatement[x] present => clinicalStatus is resolved/remission/inactive
        # con-5  clinicalStatus required when category is problem-list-item and
        #        verificationStatus is not entered-in-error
        # code (example binding), severity / bodySite / stage (example) are not
        # hard-enforced.
        invariants=list(CONDITION_INVARIANTS),
        duplicate_key_fn=condition_duplicate_key,
        search_params=dict(COMMON_SEARCH),
    ),
    # https://hl7.org/fhir/R4B/allergyintolerance.html
    "AllergyIntolerance": ResourceSpec(
        resource_type="AllergyIntolerance",
        collection="AllergyIntolerance",
        # spec min=1: AllergyIntolerance.patient (1..1). clinicalStatus /
        # verificationStatus / type / category / criticality / code are all
        # 0..1 or 0..* in R4B, enforced conditionally via ait-1/ait-2 and the
        # value-set bindings below rather than as hard-required elements.
        required_fields=["patient"],
        value_sets={
            # clinicalStatus / verificationStatus - required bindings, checked
            # only when sent (both are 0..1 elements)
            "clinicalStatus.coding.code": _ALLERGYINTOLERANCE_CLINICAL_STATUS,
            "verificationStatus.coding.code": _ALLERGYINTOLERANCE_VERIFICATION_STATUS,
            # type - required binding, element is 0..1: checked only when sent
            "type": _ALLERGYINTOLERANCE_TYPE,
            # category - required binding, element is 0..*: checked only when sent
            "category": _ALLERGYINTOLERANCE_CATEGORY,
            # criticality - required binding, element is 0..1: checked only when sent
            "criticality": _ALLERGYINTOLERANCE_CRITICALITY,
        },
        # ait-1  clinicalStatus SHALL NOT be present if verificationStatus is
        #        entered-in-error
        # ait-2  clinicalStatus required when verificationStatus is not
        #        entered-in-error
        # code (extensible, RxNorm/SNOMED), reaction.substance / reaction.manifestation
        # (example) are not hard-enforced.
        invariants=list(ALLERGYINTOLERANCE_INVARIANTS),
        duplicate_key_fn=allergyintolerance_duplicate_key,
        search_params=dict(_ALLERGYINTOLERANCE_SEARCH),
    ),
}
