from modules.detection.analyzer.detector_selector import DetectorSelector


def test_low_cost_routes_use_expensive_gliner_last_when_medspacy_applies():
    selector = DetectorSelector()

    assert selector.route_for_domain("financial") == ("regex", "presidio", "gliner")
    assert selector.route_for_domain("corporate") == ("regex", "presidio", "gliner")
    assert selector.route_for_domain("generic") == ("regex", "presidio", "gliner")
    assert selector.route_for_domain("healthcare") == (
        "regex",
        "presidio",
        "medspacy",
        "gliner",
    )
    assert selector.route_for_domain("mixed") == (
        "regex",
        "presidio",
        "medspacy",
        "gliner",
    )


def test_medspacy_is_restricted_to_healthcare_or_mixed_strategy():
    selector = DetectorSelector()

    financial = selector.select("Bank statement Account holder: Ravi Kumar")
    healthcare = selector.select("Patient diagnosis medication treatment")
    mixed = selector.select("Invoice contract amount due effective date")

    assert financial.use_presidio is True
    assert financial.use_gliner is True
    assert financial.use_medspacy is False
    assert healthcare.use_medspacy is True
    assert mixed.use_medspacy is True


def test_document_type_hint_can_drive_detection_domain():
    selector = DetectorSelector()

    assert selector.classify_domain("plain text", document_type="INVOICE") == "financial"
    assert selector.classify_domain("plain text", document_type="MEDICAL_RECORD") == "healthcare"
    assert selector.classify_domain("Patient diagnosis", document_type="INVOICE") == "healthcare"
    assert selector.classify_domain("Bank statement", document_type="UNKNOWN") == "financial"
