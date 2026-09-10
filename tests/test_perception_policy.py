from perception_policy import evaluate_detections


def test_person_in_agv_path_triggers_emergency_brake():
    result = evaluate_detections([[260, 220, 390, 470]], ["person"], [0.95], (640, 480))
    assert result["action"] == "EMERGENCY_BRAKE"
    assert result["severity"] == "CRITICAL"
    assert result["hazard_zone"] == "AGV_PATH"


def test_person_outside_path_is_monitored_not_braked():
    result = evaluate_detections([[0, 20, 100, 180]], ["person"], [0.90], (640, 480))
    assert result["action"] == "SLOW_AND_MONITOR"
    assert result["hazard_zone"] == "OUTER_ZONE"


def test_pallet_requires_reroute():
    result = evaluate_detections([[260, 220, 390, 470]], ["pallet"], [0.89], (640, 480))
    assert result["action"] == "REROUTE"
    assert result["severity"] == "MEDIUM"


def test_unrecognised_class_keeps_path_clear():
    result = evaluate_detections([[260, 220, 390, 470]], ["chair"], [0.89], (640, 480))
    assert result["action"] == "PATH_CLEAR"
