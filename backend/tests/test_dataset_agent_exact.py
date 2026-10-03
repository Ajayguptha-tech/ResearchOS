"""Test suite validating exact-relevance Dataset Recommendation Agent.

Tests:
- TEST J: Dataset exact-matching
- TEST K: Related dataset filtering (e.g. no Fashion-MNIST or CIFAR-10 when MNIST is requested)
- TEST L: Duplicate dataset prevention
- TEST M: Exact dataset URL verification and no generic fallback repository cards
"""

import pytest
from ai.agents.dataset_recommendation_agent import DatasetRecommendationAgent


@pytest.fixture
def agent():
    return DatasetRecommendationAgent()


def test_exact_match_mnist(agent):
    """When user requests MNIST handwritten digits, return ONLY MNIST, not Fashion-MNIST or CIFAR-10."""
    result = agent.recommend("MNIST handwritten digit dataset")
    recs = result["recommendations"]
    assert len(recs) == 1
    assert "MNIST" in recs[0]["name"]
    # Verify no related/alternative datasets were slipped in
    names = [r["name"] for r in recs]
    assert "Fashion-MNIST" not in names
    assert "CIFAR-10" not in names
    assert "ImageNet" not in names
    assert "yann.lecun.com" in recs[0]["url"]
    assert len(result["general_repositories"]) == 0


def test_exact_match_uci_iris(agent):
    """When user requests UCI Iris dataset, return ONLY Iris, not Wine Quality, Breast Cancer, or Abalone."""
    result = agent.recommend("Give me the UCI Iris dataset")
    recs = result["recommendations"]
    assert len(recs) == 1
    assert "Iris" in recs[0]["name"]
    names = [r["name"] for r in recs]
    assert "Wine Quality Dataset" not in names
    assert "Breast Cancer Wisconsin (Diagnostic)" not in names
    assert "archive.ics.uci.edu" in recs[0]["url"]
    assert len(result["general_repositories"]) == 0


def test_exact_match_credit_card_fraud(agent):
    """When user requests credit card fraud detection on Kaggle, return the exact dataset."""
    result = agent.recommend("Give me Kaggle datasets for credit card fraud detection")
    recs = result["recommendations"]
    assert len(recs) == 1
    assert "Credit Card Fraud Detection" in recs[0]["name"]
    assert "kaggle.com" in recs[0]["url"]
    assert "fraud" in recs[0]["use"].lower()


def test_covid_chest_xray_filtering(agent):
    """When user requests COVID-19 chest X-ray, do NOT return general chest X-ray datasets like CheXpert."""
    result = agent.recommend("COVID-19 chest X-ray dataset")
    recs = result["recommendations"]
    assert len(recs) >= 1
    for r in recs:
        assert "covid" in r["name"].lower() or "covid" in r["purpose"].lower()
        # CheXpert is general chest radiographs without COVID labels — must NOT be returned
        assert "chexpert" not in r["name"].lower()


def test_handwritten_digit_recognition_task(agent):
    """When user asks for datasets for handwritten digit recognition, return datasets containing handwritten digits."""
    result = agent.recommend("Give me datasets for handwritten digit recognition")
    recs = result["recommendations"]
    assert len(recs) >= 1
    for r in recs:
        assert "digit" in r["purpose"].lower() or "digit" in r["use"].lower()
    # Confirm no Fashion-MNIST or CIFAR-10
    names = [r["name"] for r in recs]
    assert "Fashion-MNIST" not in names
    assert "CIFAR-10" not in names


def test_requested_count_enforcement_no_padding(agent):
    """If user requests 5 datasets for credit card fraud, return only the verified exact matches, do NOT pad with unrelated datasets."""
    result = agent.recommend("Give me exactly 5 datasets for credit card fraud detection")
    recs = result["recommendations"]
    # Only 1 exact match exists in the catalog for this specific task
    assert len(recs) == 1
    assert "Only 1 exact match(es) could be verified; no unrelated datasets were substituted." in result["message"]


def test_no_exact_match_returns_clean_message_and_empty_list(agent):
    """If user asks for something with no exact match, return empty list and clear notification message."""
    result = agent.recommend("Antigravity tachyon pulse warp drive dataset")
    assert len(result["recommendations"]) == 0
    assert result["message"] == "No exact dataset matching the requested criteria could be verified."
    # Never return generic portal fallbacks
    assert len(result["general_repositories"]) == 0


def test_duplicate_prevention(agent):
    """Ensure no duplicates exist in output."""
    result = agent.recommend("Cora citation network and graph neural networks on Cora")
    recs = result["recommendations"]
    cora_count = sum(1 for r in recs if "cora" in r["name"].lower())
    assert cora_count == 1
    # Check all URLs are unique
    urls = [r["url"] for r in recs if r.get("url")]
    assert len(urls) == len(set(urls))


def test_exact_url_verification(agent):
    """Verify that returned datasets contain non-empty, valid canonical URLs."""
    result = agent.recommend("Graph Neural Networks", [{"title": "Study on Cora and CiteSeer"}])
    recs = result["recommendations"]
    assert len(recs) >= 1
    for r in recs:
        assert r["url"].startswith("http://") or r["url"].startswith("https://")
        assert len(r["why_matched"]) > 10
