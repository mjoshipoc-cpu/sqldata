"""
Shared registry building blocks: the ResourceSpec shape, value-set bindings
that apply to every resource, and search-param mappings shared by more than
one module.

Module registries (registry/diagnostic.py, registry/clinical.py, ...) import
from here; they do not import from each other.

Pure stdlib - no flask, no fhir.resources.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


# ---------------------------------------------------------------------------
# value sets that apply to every resource (FHIR datatype-level bindings)
# ---------------------------------------------------------------------------
COMMON_VALUE_SETS: dict[str, set[str]] = {
    "telecom.system": {"phone", "fax", "email", "pager", "url", "sms", "other"},
    "identifier.use": {"usual", "official", "temp", "secondary", "old"},
    "name.use": {"usual", "official", "temp", "nickname", "anonymous", "old", "maiden"},
}


# ---------------------------------------------------------------------------
# ResourceSpec
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResourceSpec:
    """Everything the pipeline needs to know about one FHIR resource type."""

    resource_type: str
    collection: str
    # Conformance profile URL to validate against (US Core / IPS / ABDM / ...).
    # None = base-spec structural validation only.
    profile: str | None = None
    # Each item is either a field name, or a tuple of field names meaning
    # "at least one of these must be present" (choice-type / [x] elements).
    required_fields: list = field(default_factory=list)
    # dot-path -> allowed values, e.g. "status" or "code.coding.code".
    value_sets: dict[str, set[str]] = field(default_factory=dict)
    # cross-element invariant checks (obs-6, obs-7, ...). Added in step 5-6;
    # each is  fn(resource_dict) -> list[issue-dict]  (empty list = OK).
    invariants: list[Callable[[dict], list[dict]]] = field(default_factory=list)
    # fn(resource_dict) -> Mongo query dict, or None if no business key can be
    # formed. Only run on create.
    duplicate_key_fn: Callable[[dict], dict | None] | None = None
    # search param name -> Mongo field path (on the stored document).
    search_params: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# search-param mapping shared by resources that key their person-reference on
# `subject` (most of the Diagnostic Module + Condition). AllergyIntolerance
# keys on `patient` instead and defines its own map in registry/clinical.py.
# ---------------------------------------------------------------------------
COMMON_SEARCH = {
    "_id": "ResourceId",
    "identifier": "ResourceData.identifier.value",
    "status": "ResourceData.status",
    "subject": "ResourceData.subject.reference",
    "patient": "ResourceData.subject.reference",
    "code": "ResourceData.code.coding.code",
}
