from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_sum() -> None:
    response = client.get("/api/calc/sum", params={"a": 2, "b": 3})
    assert response.status_code == 200
    assert response.json() == {"result": 5}


def test_sum_negative() -> None:
    response = client.get("/api/calc/sum", params={"a": -4, "b": 1})
    assert response.status_code == 200
    assert response.json() == {"result": -3}


def test_sum_missing_param() -> None:
    response = client.get("/api/calc/sum", params={"a": 1})
    assert response.status_code == 422
