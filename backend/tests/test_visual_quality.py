from backend.visual_quality import analyze_visual_snapshots


def test_visual_quality_detects_out_of_frame_text():
    payload = {
        "frame": {"x_radius": 7.0, "y_radius": 4.0},
        "snapshots": [
            {
                "event": "play",
                "mobjects": [
                    {
                        "id": "Text:1",
                        "type": "Text",
                        "is_text": True,
                        "bounds": {
                            "left": -8.2,
                            "right": -6.9,
                            "top": 1.0,
                            "bottom": 0.2,
                        },
                    }
                ],
            }
        ],
    }

    report = analyze_visual_snapshots(payload, mode="balanced")
    assert report.passed is False
    assert any(issue.issue_type == "out_of_frame" for issue in report.issues)


def test_visual_quality_detects_text_overlap_error():
    payload = {
        "frame": {"x_radius": 7.0, "y_radius": 4.0},
        "snapshots": [
            {
                "event": "play",
                "mobjects": [
                    {
                        "id": "Text:1",
                        "type": "Text",
                        "is_text": True,
                        "bounds": {
                            "left": -1.0,
                            "right": 1.0,
                            "top": 1.0,
                            "bottom": -1.0,
                        },
                    },
                    {
                        "id": "MathTex:2",
                        "type": "MathTex",
                        "is_text": True,
                        "bounds": {
                            "left": -0.8,
                            "right": 1.2,
                            "top": 0.9,
                            "bottom": -1.1,
                        },
                    },
                ],
            }
        ],
    }

    report = analyze_visual_snapshots(payload, mode="balanced")
    assert report.error_count >= 1
    assert any(issue.issue_type == "text_overlap" for issue in report.issues)


def test_visual_quality_passes_clean_layout():
    payload = {
        "frame": {"x_radius": 7.0, "y_radius": 4.0},
        "snapshots": [
            {
                "event": "play",
                "mobjects": [
                    {
                        "id": "Text:1",
                        "type": "Text",
                        "is_text": True,
                        "bounds": {
                            "left": -5.0,
                            "right": -2.0,
                            "top": 3.0,
                            "bottom": 2.2,
                        },
                    },
                    {
                        "id": "MathTex:2",
                        "type": "MathTex",
                        "is_text": True,
                        "bounds": {
                            "left": 1.0,
                            "right": 4.0,
                            "top": -2.2,
                            "bottom": -3.0,
                        },
                    },
                ],
            }
        ],
    }

    report = analyze_visual_snapshots(payload, mode="balanced")
    assert report.passed is True
    assert report.error_count == 0
    assert report.score >= 85
