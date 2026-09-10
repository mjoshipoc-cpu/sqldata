"""
Diagnostic Module registry - order/result resources (data carried over from
utils/fhir_validation/config.py): Observation, DiagnosticReport, ServiceRequest,
DocumentReference, ImagingStudy.

Pure stdlib - no flask, no fhir.resources.
"""
from __future__ import annotations

from fhirpipeline.invariants.observation import OBSERVATION_INVARIANTS
from fhirpipeline.invariants.servicerequest import SERVICEREQUEST_INVARIANTS
from fhirpipeline.registry.base import ResourceSpec, COMMON_SEARCH


# ---------------------------------------------------------------------------
# duplicate-key functions (pure - no DB, no flask)
# ---------------------------------------------------------------------------
def observation_duplicate_key(resource: dict) -> dict | None:
    """
    Business key for Observation: same subject + same code + same effective
    instant. Returns None when there isn't enough to form a key (caller then
    falls back to id-only dedup).
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

    effective = (resource.get("effectiveDateTime")
                 or (resource.get("effectivePeriod") or {}).get("start"))
    if not effective:
        return None

    query: dict = {
        "DeletedFlag": 0,
        "ResourceData.subject.reference": subject_ref,
        "ResourceData.code.coding.code": code,
        "$or": [
            {"ResourceData.effectiveDateTime": effective},
            {"ResourceData.effectivePeriod.start": effective},
        ],
    }
    if system:
        query["ResourceData.code.coding.system"] = system
    return query


# ---------------------------------------------------------------------------
# value sets
# ---------------------------------------------------------------------------
# Observation.status - required binding (ObservationStatus)
# https://hl7.org/fhir/R4B/valueset-observation-status.html
_OBSERVATION_STATUS = {
    "registered", "preliminary", "final", "amended",
    "corrected", "cancelled", "entered-in-error", "unknown",
}
# Observation.category - preferred binding (observation-category)
# https://hl7.org/fhir/R4B/valueset-observation-category.html
_OBSERVATION_CATEGORY = {
    "social-history", "vital-signs", "imaging", "laboratory",
    "procedure", "survey", "exam", "therapy", "activity",
}
# Observation.referenceRange.type - preferred binding (referencerange-meaning)
# https://hl7.org/fhir/R4B/valueset-referencerange-meaning.html
_REFERENCERANGE_MEANING = {
    "type", "normal", "recommended", "treatment", "target", "pre", "post",
}
# Quantity.comparator - required binding (QuantityComparator, R4B).
# Datatype-level: applies to Observation.valueQuantity + component.valueQuantity
# (referenceRange.low/high are SimpleQuantity, where comparator is prohibited).
_QTY_COMPARATOR = {"<", "<=", ">=", ">"}
_DIAGNOSTICREPORT_STATUS = {
    "registered", "partial", "preliminary", "final", "amended",
    "corrected", "appended", "cancelled", "entered-in-error", "unknown",
}
_IMAGINGSTUDY_STATUS = {"registered", "available", "cancelled", "entered-in-error", "unknown"}
# DocumentReference.status - required binding (document-reference-status)
_DOCUMENTREFERENCE_STATUS = {"current", "superseded", "entered-in-error"}
# DocumentReference.docStatus - required binding (composition-status, R4B)
_DOCUMENTREFERENCE_DOCSTATUS = {"preliminary", "final", "amended", "entered-in-error"}
# DocumentReference.relatesTo.code - required binding (document-relationship-type)
_DOCUMENTREFERENCE_RELATESTO = {"replaces", "transforms", "signs", "appends"}
_SERVICEREQUEST_STATUS = {
    "draft", "active", "on-hold", "revoked", "completed", "entered-in-error", "unknown",
}
_SERVICEREQUEST_INTENT = {
    "proposal", "plan", "directive", "order", "original-order",
    "reflex-order", "filler-order", "instance-order", "option",
}
_SERVICEREQUEST_PRIORITY = {"routine", "urgent", "asap", "stat"}


# ---------------------------------------------------------------------------
# the registry - Diagnostic Module
# ---------------------------------------------------------------------------
DIAGNOSTIC_REGISTRY: dict[str, ResourceSpec] = {
    # https://hl7.org/fhir/R4B/observation.html
    "Observation": ResourceSpec(
        resource_type="Observation",
        collection="Observation",
        # spec min=1: Observation.status (1..1), Observation.code (1..1).
        # subject is 0..1 in R4B, so it is NOT required here.
        required_fields=["status", "code"],
        value_sets={
            # status - required binding, enforced strictly
            "status": _OBSERVATION_STATUS,
            # valueQuantity.comparator - required binding, checked only when sent
            "valueQuantity.comparator": _QTY_COMPARATOR,
            "component.valueQuantity.comparator": _QTY_COMPARATOR,
            # category / referenceRange.type - preferred bindings, checked only
            # when sent. NOTE: _check_value_sets is system-blind, so a legitimate
            # secondary coding from a non-HL7 system on the same concept would be
            # flagged.
            "category.coding.code": _OBSERVATION_CATEGORY,
            "referenceRange.type.coding.code": _REFERENCERANGE_MEANING,
            "component.referenceRange.type.coding.code": _REFERENCERANGE_MEANING,
        },
        # obs-3  each referenceRange has a low, a high, or text
        # obs-6  dataAbsentReason only when value[x] is absent
        # obs-7  code == a component.code  =>  no top-level value[x]
        # (local) carries a result somewhere            -> warning only
        # code / bodySite / method are example bindings; dataAbsentReason /
        # interpretation are extensible bindings in R4B - none are hard-enforced.
        invariants=list(OBSERVATION_INVARIANTS),
        duplicate_key_fn=observation_duplicate_key,
        search_params=dict(COMMON_SEARCH),
    ),
    # https://hl7.org/fhir/R4B/diagnosticreport.html
    "DiagnosticReport": ResourceSpec(
        resource_type="DiagnosticReport",
        collection="DiagnosticReport",
        # spec min=1: DiagnosticReport.status (1..1), DiagnosticReport.code (1..1).
        required_fields=["status", "code"],
        value_sets={
            # status - required binding, enforced strictly
            "status": _DIAGNOSTICREPORT_STATUS,
        },
        # code (preferred, LOINC), category / conclusionCode (example) are not
        # enumerable and are not hard-enforced. R4B lists no constraint invariants.
        search_params=dict(COMMON_SEARCH),
    ),
    # https://hl7.org/fhir/R4B/servicerequest.html
    "ServiceRequest": ResourceSpec(
        resource_type="ServiceRequest",
        collection="ServiceRequest",
        # spec min=1: status (1..1), intent (1..1), subject (1..1).
        required_fields=["status", "intent", "subject"],
        value_sets={
            # status / intent - required bindings, enforced strictly
            "status": _SERVICEREQUEST_STATUS,
            "intent": _SERVICEREQUEST_INTENT,
            # priority - required binding, but the element is 0..1: checked only
            # when a priority is sent
            "priority": _SERVICEREQUEST_PRIORITY,
            # quantityQuantity.comparator - required binding, checked only when sent
            "quantityQuantity.comparator": _QTY_COMPARATOR,
        },
        # prr-1: orderDetail only if code is present.
        # code / category / bodySite / reasonCode are example bindings - not
        # hard-enforced.
        invariants=list(SERVICEREQUEST_INVARIANTS),
        search_params=dict(COMMON_SEARCH),
    ),
    # https://hl7.org/fhir/R4B/documentreference.html
    "DocumentReference": ResourceSpec(
        resource_type="DocumentReference",
        collection="DocumentReference",
        # spec min=1: status (1..1), content (1..*).
        required_fields=["status", "content"],
        value_sets={
            # status - required binding, enforced strictly
            "status": _DOCUMENTREFERENCE_STATUS,
            # docStatus - required binding, element is 0..1: checked only when sent
            "docStatus": _DOCUMENTREFERENCE_DOCSTATUS,
            # relatesTo.code - required binding, mandatory inside each relatesTo
            "relatesTo.code": _DOCUMENTREFERENCE_RELATESTO,
        },
        # type (preferred, LOINC), category / context.* (example), securityLabel
        # (extensible) are not hard-enforced. R4B lists no constraint invariants.
        search_params={k: v for k, v in COMMON_SEARCH.items() if k != "code"},
    ),
    # https://hl7.org/fhir/R4B/imagingstudy.html
    "ImagingStudy": ResourceSpec(
        resource_type="ImagingStudy",
        collection="ImagingStudy",
        # spec min=1: status (1..1), subject (1..1).
        required_fields=["status", "subject"],
        value_sets={
            # status - required binding, enforced strictly
            "status": _IMAGINGSTUDY_STATUS,
        },
        # modality / series.modality / procedureCode / sopClass are extensible
        # DICOM bindings; laterality / bodySite are example - none are
        # hard-enforced. R4B lists no constraint invariants.
        search_params={k: v for k, v in COMMON_SEARCH.items() if k != "code"},
    ),
}
