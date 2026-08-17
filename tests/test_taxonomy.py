import pytest
from modules.detection.taxonomy import TaxonomyService

def test_taxonomy_priority_lookup():
    # Medical record MUST_HAVE
    assert TaxonomyService.is_must_have("FULL NAME / PERSON NAME", "Medical Record / Clinical Note") is True
    assert TaxonomyService.is_must_have("MEDICAL RECORD NUMBER (MRN)", "Medical Record / Clinical Note") is True
    assert TaxonomyService.should_mask("FULL NAME / PERSON NAME", "Medical Record / Clinical Note") is True

    # Medical record DROP
    assert TaxonomyService.is_drop("MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER", "Lab Report / Pathology Report") is True
    assert TaxonomyService.should_target("MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER", "Lab Report / Pathology Report") is False
    assert TaxonomyService.should_mask("MEDICAL EQUIPMENT/INSTRUMENT SERIAL NUMBER", "Lab Report / Pathology Report") is False

def test_canonicalize_aliases():
    assert TaxonomyService.canonicalize("DOB") == "DATE OF BIRTH"
    assert TaxonomyService.canonicalize("MRN") == "MEDICAL RECORD NUMBER (MRN)"
    assert TaxonomyService.canonicalize("SSN") == "SOCIAL SECURITY NUMBER (SSN)"
    assert TaxonomyService.canonicalize("Aadhaar") == "AADHAAR NUMBER (INDIA)"

def test_target_entities_for_llm():
    targets = TaxonomyService.get_target_entities("Prescription")
    assert "MUST_HAVE" in targets
    assert "NICE_TO_HAVE" in targets
    assert len(targets["MUST_HAVE"]) > 0
    assert any("MEDICATION" in ent for ent in targets["MUST_HAVE"])
