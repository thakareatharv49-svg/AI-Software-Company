from company.reliability import ReliabilityController, ReliabilityEvent


def test_incident_detection_and_resolution() -> None:
    reliability = ReliabilityController()
    incident = reliability.observe(ReliabilityEvent("critical-db", False, "db down"))
    assert incident is not None
    assert not incident.resolved
    reliability.resolve(incident.id)
    assert reliability.health()["healthy"]
