"""Shared API tests, run against both the native and snake-guice apps.

Every test below runs twice (once per `client` fixture param) — passing
proves the two dependency-injection approaches produce a functionally
identical API.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from examples.fastapi_tasks.fastapi_native.main import create_app as create_native_app
from examples.fastapi_tasks.fastapi_snakeguice.main import (
    create_app as create_snakeguice_app,
)

FACTORIES: dict[str, Callable[[str], FastAPI]] = {
    "native": create_native_app,
    "snakeguice": create_snakeguice_app,
}


@pytest.fixture(params=["native", "snakeguice"])
def client(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[TestClient]:
    db_path = str(tmp_path / "tasks.db")
    with TestClient(FACTORIES[request.param](db_path)) as test_client:
        yield test_client


def test_list_empty(client: TestClient) -> None:
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_create_task(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "write tests"})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "write tests"
    assert body["done"] is False
    assert "id" in body
    assert "created_at" in body


def test_get_task(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "write tests"}).json()

    response = client.get(f"/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_task_404(client: TestClient) -> None:
    response = client.get("/tasks/999")
    assert response.status_code == 404


def test_list_after_create(client: TestClient) -> None:
    client.post("/tasks", json={"title": "first"})
    client.post("/tasks", json={"title": "second"})

    response = client.get("/tasks")

    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == ["first", "second"]


def test_update_task_title(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "old title"}).json()

    response = client.patch(f"/tasks/{created['id']}", json={"title": "new title"})

    assert response.status_code == 200
    assert response.json()["title"] == "new title"


def test_update_task_done(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "task"}).json()

    response = client.patch(f"/tasks/{created['id']}", json={"done": True})

    assert response.status_code == 200
    assert response.json()["done"] is True


def test_update_task_404(client: TestClient) -> None:
    response = client.patch("/tasks/999", json={"done": True})
    assert response.status_code == 404


def test_delete_task(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "task"}).json()

    response = client.delete(f"/tasks/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/tasks/{created['id']}")
    assert response.status_code == 404


def test_delete_task_404(client: TestClient) -> None:
    response = client.delete("/tasks/999")
    assert response.status_code == 404


def test_stats_track_created_and_completed(client: TestClient) -> None:
    first = client.post("/tasks", json={"title": "first"}).json()
    client.post("/tasks", json={"title": "second"})
    client.patch(f"/tasks/{first['id']}", json={"done": True})

    response = client.get("/stats")

    assert response.status_code == 200
    assert response.json() == {"created": 2, "completed": 1}
