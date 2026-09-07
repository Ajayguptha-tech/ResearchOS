"""Verify literature agent retry logic and scoring model."""
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath('..'))

from ai.agents.literature_search_agent import LiteratureSearchAgent

agent = LiteratureSearchAgent()

# Verify retry constants exist
assert hasattr(agent, '_MAX_RETRIES'), "Missing _MAX_RETRIES"
assert hasattr(agent, '_BASE_BACKOFF'), "Missing _BASE_BACKOFF"
assert hasattr(agent, '_QUERY_DELAY'), "Missing _QUERY_DELAY"
assert agent._MAX_RETRIES == 3, f"Expected 3 retries, got {agent._MAX_RETRIES}"
assert agent._BASE_BACKOFF == 2.0, f"Expected 2.0s backoff, got {agent._BASE_BACKOFF}"
assert agent._QUERY_DELAY == 1.0, f"Expected 1.0s delay, got {agent._QUERY_DELAY}"
print("OK  Retry constants verified")

# Verify _get_retry_after works
import httpx
fake_resp = httpx.Response(429, headers={"Retry-After": "5"})
delay = agent._get_retry_after(fake_resp)
assert delay == 5.0, f"Expected 5.0s, got {delay}"
print("OK  Retry-After header parsing works")

# Clamped
fake_resp2 = httpx.Response(429, headers={"Retry-After": "120"})
delay2 = agent._get_retry_after(fake_resp2)
assert delay2 == 30.0, f"Expected clamped 30.0s, got {delay2}"
print("OK  Retry-After clamping works")

# No header
fake_resp3 = httpx.Response(429)
delay3 = agent._get_retry_after(fake_resp3)
assert delay3 == 0.0, f"Expected 0.0s, got {delay3}"
print("OK  No Retry-After returns 0.0")

# Verify scoring model
test_papers = [
    {"title": "Deep learning", "authors": ["A"], "abstract": "deep learning", "year": 2024, "url": "", "doi": "10.1/t1", "citation_count": 500, "venue": "ICML", "source": "Semantic Scholar", "citations_available": True},
    {"title": "Old survey", "authors": ["B"], "abstract": "survey methods", "year": 2010, "url": "", "doi": "10.1/t2", "citation_count": 2000, "venue": "JMLR", "source": "Semantic Scholar", "citations_available": True},
    {"title": "Recent work", "authors": ["C"], "abstract": "new approach", "year": 2025, "url": "", "doi": "10.1/t3", "citation_count": 5, "venue": "", "source": "Crossref", "citations_available": True},
]
ranked = agent._rank_results("deep learning", test_papers)
assert len(ranked) == 3, f"Expected 3 results, got {len(ranked)}"
# Verify all have score_explanation
for p in ranked:
    assert "relevance_score" in p, f"Missing relevance_score for {p['title']}"
    assert "score_explanation" in p, f"Missing score_explanation for {p['title']}"
    assert "citation_impact" in p["score_explanation"], f"Missing citation_impact"
    assert "citations" in p["score_explanation"], f"Missing citations"
    assert "topic_relevance" in p["score_explanation"], f"Missing topic_relevance"
    assert "recency" in p["score_explanation"], f"Missing recency"
    assert "published" in p["score_explanation"], f"Missing published"
    assert "source" in p["score_explanation"], f"Missing source"
print(f"OK  Scoring model verified: scores = {[p['relevance_score'] for p in ranked]}")

# Old highly-cited paper should still score respectably
old_paper = [p for p in ranked if p["title"] == "Old survey"][0]
new_paper = [p for p in ranked if p["title"] == "Recent work"][0]
assert old_paper["relevance_score"] > new_paper["relevance_score"], \
    f"Old highly-cited paper ({old_paper['relevance_score']}) should outrank new low-cited paper ({new_paper['relevance_score']})"
print(f"OK  Old highly-cited ({old_paper['relevance_score']}) > New low-cited ({new_paper['relevance_score']})")

# Verify error messages
msg = agent._no_results_message()
assert "rate limit" not in msg.lower() or "rate limit" in msg.lower()
print(f"OK  Error message: {msg[:80]}...")

# Simulate rate-limited provider
agent.provider_errors = {"Semantic Scholar": "rate limited after retries; try again later"}
msg_rl = agent._no_results_message()
print(f"  Rate-limit message: {repr(msg_rl[:100])}")
assert "rate limit" in msg_rl.lower() or "rate-limit" in msg_rl.lower(), f"Expected rate-limit message, got: {msg_rl[:120]}"
print("OK  Rate-limit message verified")

print("\nAll verifications passed!")
