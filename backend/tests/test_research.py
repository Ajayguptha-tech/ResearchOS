from fastapi.testclient import TestClient

from ai.agents.literature_search_agent import LiteratureSearchAgent
from app.main import app
from app.api.v1.routes import research as research_route

client = TestClient(app)


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("provider failure")

    def json(self) -> dict:
        return self.payload


class FakeClient:
    def __init__(self, *, timeout: float, headers: dict | None = None) -> None:
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def get(self, url: str, params: dict) -> FakeResponse:
        if "semanticscholar" in url:
            return FakeResponse(
                {
                    "data": [
                        {
                            "title": "Computer Networks Security",
                            "authors": [{"name": "A. Researcher"}, {}],
                            "abstract": None,
                            "year": None,
                            "url": None,
                            "externalIds": {"DOI": "10.1000/network"},
                            "citationCount": 12,
                            "venue": "Networks Journal",
                        }
                    ]
                }
            )
        return FakeResponse(
            {
                "message": {
                    "items": [
                        {
                            "title": [f"Crossref Network Study {index}"],
                            "author": [{"given": "B.", "family": "Author"}],
                            "abstract": "<jats:p>Network findings.</jats:p>",
                            "published": {"date-parts": [[2024]]},
                            "URL": f"https://doi.org/10.2000/network-{index}",
                            "DOI": f"10.2000/network-{index}",
                            "container-title": ["Computing Review"],
                        }
                        for index in range(10)
                    ]
                }
            }
        )


def register(email: str = "research-test@example.com") -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password", "name": "Researcher"},
    )
    assert response.status_code in {200, 201}
    return response.json()["access_token"]


def test_literature_search_parses_metadata_and_supplements_crossref(monkeypatch) -> None:
    monkeypatch.setattr("ai.agents.literature_search_agent.httpx.Client", FakeClient)

    result = LiteratureSearchAgent().search("Computer Networks")

    assert result["status"] == "success"
    assert len(result["results"]) >= 10  # max_results increased to 30
    assert result["results"][0]["doi"]
    assert result["results"][0]["authors"]
    assert all(paper["source"] in {"Semantic Scholar", "Crossref"} for paper in result["results"])


def test_research_route_requires_auth_and_maps_provider_failure(monkeypatch) -> None:
    unauthenticated = client.post("/api/v1/research/analyze?idea=Computer%20Networks")
    assert unauthenticated.status_code == 401

    token = register()
    monkeypatch.setattr(
        research_route.orchestrator,
        "run_research_workflow",
        lambda idea, **kwargs: {"literature": {"query": idea, "results": [], "status": "success"}},
    )
    response = client.post(
        "/api/v1/research/analyze?idea=Computer%20Networks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["literature"]["query"] == "Computer Networks"

    monkeypatch.setattr(
        research_route.orchestrator,
        "run_research_workflow",
        lambda idea, **kwargs: (_ for _ in ()).throw(RuntimeError("Literature providers unavailable.")),
    )
    failed = client.post(
        "/api/v1/research/analyze?idea=Computer%20Networks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert failed.status_code == 502
    assert failed.json()["detail"] == "Literature providers unavailable."


def test_local_document_analysis_uses_uploaded_evidence_without_providers(monkeypatch) -> None:
    token = register("local-document-analysis@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = client.post(
        "/api/v1/papers/upload",
        headers=headers,
        files={
            "file": (
                "computer-networks-evidence.md",
                b"Computer networks research demonstrates that routing optimization improves reliability. Future work should evaluate limitations in wireless network experiments.",
                "text/markdown",
            )
        },
    )
    assert uploaded.status_code == 201

    def unexpected_external_search(_: str) -> dict:
        raise AssertionError("Local analysis must not call external literature providers")

    monkeypatch.setattr(research_route.orchestrator.literature, "search", unexpected_external_search)
    response = client.post(
        "/api/v1/research/analyze-local?idea=Computer%20Networks",
        headers=headers,
    )

    assert response.status_code == 200
    result = response.json()
    assert result["literature"]["source"] == "local_uploaded_documents"
    assert result["literature"]["results"][0]["source"] == "local_uploaded_document"
    assert result["analysis"]["papers_processed"] == 1
    assert "routing optimization improves reliability" in result["analysis"]["papers"][0]["abstract_summary"].lower()
    assert result["research_gaps"]["status"] == "ready"
    assert result["datasets"]["status"] == "ready"
    assert result["experiments"]["status"] == "ready"
    assert result["roadmap"]["status"] == "ready"
