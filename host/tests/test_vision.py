from robot_host.vision import Detection, PedestrianSafety


FRAME_W = 640
FRAME_H = 480


def test_clear_when_no_pedestrian():
    safety = PedestrianSafety()
    decision = safety.evaluate([], FRAME_W, FRAME_H)
    assert decision.action == "clear"
    assert decision.speed_scale == 1.0


def test_stop_when_pedestrian_is_large():
    safety = PedestrianSafety()
    person = Detection(200, 100, 440, 460, 0.9, "person")
    decision = safety.evaluate([person], FRAME_W, FRAME_H)
    assert decision.action == "stop"
    assert decision.speed_scale == 0.0
    assert decision.closest is person


def test_slow_when_pedestrian_is_medium():
    safety = PedestrianSafety(stop_area_ratio=0.3, slow_area_ratio=0.05, near_bottom_ratio=1.0)
    person = Detection(250, 200, 400, 420, 0.8, "person")
    decision = safety.evaluate([person], FRAME_W, FRAME_H)
    assert decision.action == "slow"
    assert 0.0 < decision.speed_scale < 1.0


def test_stop_when_pedestrian_is_close_to_bottom():
    safety = PedestrianSafety(stop_area_ratio=0.5, slow_area_ratio=0.5)
    person = Detection(280, 350, 360, 470, 0.7, "person")
    decision = safety.evaluate([person], FRAME_W, FRAME_H)
    assert decision.action == "stop"


def test_low_confidence_and_other_classes_are_ignored():
    safety = PedestrianSafety(min_confidence=0.5)
    detections = [
        Detection(200, 100, 440, 460, 0.2, "person"),
        Detection(200, 100, 440, 460, 0.99, "car"),
    ]
    decision = safety.evaluate(detections, FRAME_W, FRAME_H)
    assert decision.action == "clear"
