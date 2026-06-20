from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hello_default() -> None:
    response = client.get("/api/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, world!"}


def test_hello_with_name() -> None:
    response = client.get("/api/hello", params={"name": "Claude"})
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Claude!"}
