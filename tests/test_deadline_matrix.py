import pytest
from rads import deadline_risk

@pytest.mark.parametrize("deadline,now,queue,inference,expected", [
    (deadline, now, queue, inference, "HIGH" if now + queue + inference > deadline else "LOW")
    for deadline in (50, 100, 250, 500, 1000)
    for now in (0, 25, 75, 150, 300)
    for queue in (0, 20)
    for inference in (10, 40)
])
def test_deadline_risk_matrix(deadline, now, queue, inference, expected):
    assert deadline_risk(0, deadline, now, queue, inference) == expected
