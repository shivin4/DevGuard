def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_dashboard_route(client):
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "AI DevGuard" in res.text


def test_api_explain_error(client):
    payload = {
        "traceback_text": "Traceback (most recent call last):\n  File 'a.py', line 1\nZeroDivisionError: division by zero"
    }
    res = client.post("/api/v1/explain", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "explanation" in data
    assert data["explanation"]["exception_type"] == "ZeroDivisionError"


def test_webhook_github_ignored_event(client):
    headers = {"X-GitHub-Event": "push"}
    res = client.post("/webhooks/github", json={}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"
