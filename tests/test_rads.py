from rads import deadline_risk, deadline_urgency, rads_score

def test_deadline_urgency_increases_over_time():
    assert deadline_urgency(0, 1000, 100) < deadline_urgency(0, 1000, 900)

def test_critical_job_outranks_normal_with_equal_deadlines():
    assert rads_score("CRITICAL", 0, 1000, 100, 20) > rads_score("NORMAL", 0, 1000, 100, 20)

def test_deadline_risk_flags_predicted_miss():
    assert deadline_risk(0, 100, 50, 40, 20) == "HIGH"

def test_deadline_risk_stays_low_when_completion_fits():
    assert deadline_risk(0, 200, 50, 40, 20) == "LOW"

def test_waiting_prevents_starvation():
    fresh = rads_score("LOW", 0, 100000, 0, 20)
    aged = rads_score("LOW", 0, 100000, 30000, 20)
    assert aged > fresh
