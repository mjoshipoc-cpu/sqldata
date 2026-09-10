"""
Resource registry: one place that describes every FHIR resource type the
pipeline handles - collection name, conformance profile, required elements,
value-set bindings, cross-element invariants, duplicate-detection key, and
search parameters.

This is DATA, not logic. Downstream layers read it:
    - dispatch (step 6)      -> is this a supported resourceType?
    - validate (step 5)      -> required_fields / value_sets / invariants / profile
    - persistence (step 8)   -> collection / duplicate_key_fn / search_params

Split module-wise, mirroring routes/DiagnosticModule and routes/ClinicalModule:
    registry/base.py       -> ResourceSpec, COMMON_VALUE_SETS, COMMON_SEARCH
    registry/diagnostic.py -> DIAGNOSTIC_REGISTRY (Observation, DiagnosticReport, ...)
    registry/clinical.py   -> CLINICAL_REGISTRY (Condition, AllergyIntolerance)

Adding a new resource type to an existing module = one entry in that module's
*_REGISTRY dict, nothing else. Adding a new module = one new registry/<module>.py
exporting a *_REGISTRY dict, merged in below.

Pure stdlib - no flask, no fhir.resources.
"""
from __future__ import annotations

from fhirpipeline.registry.base import ResourceSpec, COMMON_VALUE_SETS
from fhirpipeline.registry.diagnostic import DIAGNOSTIC_REGISTRY, observation_duplicate_key
from fhirpipeline.registry.clinical import (
    CLINICAL_REGISTRY,
    condition_duplicate_key,
    allergyintolerance_duplicate_key,
)

__all__ = [
    "ResourceSpec",
    "COMMON_VALUE_SETS",
    "RESOURCE_REGISTRY",
    "get_spec",
    "is_supported",
    "observation_duplicate_key",
    "condition_duplicate_key",
    "allergyintolerance_duplicate_key",
]

RESOURCE_REGISTRY: dict[str, ResourceSpec] = {
    **DIAGNOSTIC_REGISTRY,
    **CLINICAL_REGISTRY,
}


def get_spec(resource_type: str | None) -> ResourceSpec | None:
    """ResourceSpec for a resourceType, or None if the pipeline does not handle it."""
    if not resource_type:
        return None
    return RESOURCE_REGISTRY.get(resource_type)


def is_supported(resource_type: str | None) -> bool:
    return get_spec(resource_type) is not None
