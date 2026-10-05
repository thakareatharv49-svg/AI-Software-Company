from company.reliability import ReliabilityController,ReliabilityEvent
def test_incident_detection_and_resolution():
    r=ReliabilityController(); i=r.observe(ReliabilityEvent("critical-db",False,"db down")); assert i and not i.resolved; r.resolve(i.id); assert r.health()["healthy"]
