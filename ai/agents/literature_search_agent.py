from __future__ import annotations

import math
import re
import time
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# Fast in-memory TTL cache for literature searches (15-minute expiry)
_SEARCH_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 900.0


class LiteratureSearchAgent:
    # Maximum retries per provider on 429 rate-limit
    _MAX_RETRIES = 2
    # Base delay in seconds for exponential backoff
    _BASE_BACKOFF = 0.5
    # Delay between queries to the same provider
    _QUERY_DELAY = 0.2

    def __init__(self) -> None:
        self.name = "Literature Search Agent"

        self.semantic_url = (
            "https://api.semanticscholar.org/graph/v1/paper/search"
        )

        self.crossref_url = "https://api.crossref.org/works"
        self.provider_errors: dict[str, str] = {}

    def search(self, query: str, max_results: int = 30) -> dict:
        """
        Search academic literature using the research topic.

        The agent:
        1. Builds focused academic queries.
        2. Searches Semantic Scholar (with citation data).
        3. Falls back to Crossref when necessary.
        4. Removes duplicate papers.
        5. Calculates citation-aware relevance scores.
        6. Returns the best available papers with score explanations.

        Args:
            query: Research topic or search string.
            max_results: Maximum number of papers to return (default 30, up to 100).
        """

        query = query.strip()
        self.provider_errors = {}
        max_results = min(max(max_results, 1), 100)  # clamp 1-100

        if not query:
            return {
                "query": query,
                "results": [],
                "status": "error",
                "source": "Academic Search",
                "message": "Research topic cannot be empty.",
            }

        cache_key = f"{query.lower()}:{max_results}"
        now_ts = time.time()
        if cache_key in _SEARCH_CACHE:
            ts, cached_res = _SEARCH_CACHE[cache_key]
            if now_ts - ts < _CACHE_TTL:
                logger.info("[Research] Cache HIT for literature query %r", query)
                return cached_res

        # Dynamic 20-year publication window
        current_year = datetime.now().year
        start_year = current_year - 20

        queries = self._build_queries(query)
        logger.info(
            "[Research] Searching Semantic Scholar for %r (year window: %d–%d, max: %d)",
            query, start_year, current_year, max_results,
        )

        all_results: list[dict] = []
        target = max_results + 5  # fetch a few extra for dedup margin

        # --------------------------------------------------
        # STEP 1: Semantic Scholar
        # --------------------------------------------------

        for i, search_query in enumerate(queries):
            result = self._semantic_search(
                search_query, start_year=start_year, end_year=current_year,
                limit=min(50, target),
            )

            if result:
                all_results.extend(result)

            if len(all_results) >= target:
                break

            # Small delay between queries to avoid rate-limiting
            if i < len(queries) - 1 and not self.provider_errors:
                time.sleep(self._QUERY_DELAY)

        # --------------------------------------------------
        # STEP 2: Crossref fallback / additional search
        # --------------------------------------------------

        logger.info(
            "[Research] Semantic Scholar returned %d usable records",
            len(all_results),
        )

        if len(all_results) < target // 2:
            logger.info(
                "[Research] Searching Crossref to supplement results"
            )
            for i, search_query in enumerate(queries):
                result = self._crossref_search(
                    search_query, start_year=start_year, end_year=current_year,
                    limit=min(50, target),
                )

                if result:
                    all_results.extend(result)

                if len(all_results) >= target:
                    break

                # Small delay between queries
                if i < len(queries) - 1 and not self.provider_errors:
                    time.sleep(self._QUERY_DELAY)

            logger.info(
                "[Research] Cross-provider records before deduplication: %d",
                len(all_results),
            )

        # --------------------------------------------------
        # STEP 3: Remove duplicates
        # --------------------------------------------------

        unique_results = self._remove_duplicates(all_results)

        # --------------------------------------------------
        # STEP 4: Rank by citation-aware scoring
        # --------------------------------------------------

        ranked_results = self._rank_results(query, unique_results)

        # Return up to max_results
        ranked_results = ranked_results[:max_results]

        total_found = len(ranked_results)

        output = {
            "query": query,
            "results": ranked_results,
            "total": total_found,
            "status": "success" if ranked_results else "error",
            "source": "Semantic Scholar / Crossref",
            "message": (
                f"{total_found} papers found"
                if ranked_results
                else self._no_results_message()
            ),
            "provider_errors": self.provider_errors,
        }
        if ranked_results:
            _SEARCH_CACHE[cache_key] = (now_ts, output)
        return output

    def _no_results_message(self) -> str:
        if not self.provider_errors:
            return (
                "Literature providers returned no usable papers. "
                "Try a more specific or simpler research topic."
            )

        # Check if any provider was rate-limited
        has_rate_limit = any("rate limit" in r.lower() for r in self.provider_errors.values())
        if has_rate_limit:
            return (
                "Literature providers are temporarily rate-limiting requests. "
                "Please wait a moment and try again with a simpler query, "
                "or try a different research topic."
            )

        details = "; ".join(
            f"{provider}: {reason}"
            for provider, reason in self.provider_errors.items()
        )
        return f"No literature provider is currently available. {details}"

    def _record_provider_error(
        self, provider: str, error: Exception
    ) -> None:
        if isinstance(error, httpx.TimeoutException):
            reason = "request timed out"
        elif isinstance(error, httpx.NetworkError):
            reason = "network connection failed"
        elif isinstance(error, httpx.HTTPStatusError):
            reason = "provider returned an HTTP error"
        else:
            reason = "provider returned an unusable response"
        self.provider_errors.setdefault(provider, reason)

    def _get_retry_after(self, response: httpx.Response) -> float:
        """Extract Retry-After header value, clamped to reasonable bounds."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                delay = float(retry_after)
                return min(max(delay, 1.0), 30.0)  # clamp 1–30 seconds
            except (ValueError, TypeError):
                pass
        return 0.0

    # ======================================================
    # QUERY GENERATION
    # ======================================================

    def _build_queries(self, query: str) -> list[str]:
        base = query.strip()
        queries = [base]
        if not base.lower().endswith("research"):
            queries.append(f"{base} research")
        return queries

    # ======================================================
    # SEMANTIC SCHOLAR
    # ======================================================

    def _semantic_search(
        self, query: str, start_year: int = 2006, end_year: int = 2026,
        limit: int = 10,
    ) -> list[dict]:
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": (
                "title,authors,abstract,year,url,"
                "citationCount,venue,externalIds"
            ),
            "year": f"{start_year}-{end_year}",
        }

        for attempt in range(self._MAX_RETRIES):
            try:
                with httpx.Client(timeout=20.0) as client:
                    response = client.get(self.semantic_url, params=params)

                if response.status_code == 429:
                    retry_after = self._get_retry_after(response)
                    backoff = max(retry_after, self._BASE_BACKOFF * (2 ** attempt))
                    logger.warning(
                        "[Research] Semantic Scholar rate limited (429) on attempt %d/%d, "
                        "retrying in %.1fs",
                        attempt + 1, self._MAX_RETRIES, backoff,
                    )
                    if attempt < self._MAX_RETRIES - 1:
                        time.sleep(backoff)
                        continue
                    # Final attempt exhausted
                    self.provider_errors.setdefault(
                        "Semantic Scholar",
                        "rate limited after retries; try again later or use a different topic",
                    )
                    return []

                response.raise_for_status()
                data = response.json()
                results = []
                for paper in data.get("data", []):
                    if not isinstance(paper, dict):
                        continue
                    title = paper.get("title") or ""

                    if not title:
                        continue

                    authors = [
                        author.get("name")
                        for author in paper.get("authors") or []
                        if isinstance(author, dict) and author.get("name")
                    ]

                    external_ids = paper.get("externalIds") or {}
                    citation_count = paper.get("citationCount") or 0

                    results.append(
                        {
                            "title": title,
                            "authors": authors,
                            "abstract": paper.get("abstract") or "",
                            "year": paper.get("year"),
                            "url": paper.get("url")
                            or (
                                f"https://doi.org/{external_ids.get('DOI')}"
                                if external_ids.get("DOI")
                                else ""
                            ),
                            "doi": external_ids.get("DOI", ""),
                            "citation_count": citation_count,
                            "citation_source": "Semantic Scholar",
                            "google_scholar_verified": False,
                            "google_scholar_citations": None,
                            "venue": paper.get("venue") or "",
                            "source": "Semantic Scholar",
                            "citations_available": citation_count > 0,
                        }
                    )

                return results
            except (
                httpx.TimeoutException,
                httpx.NetworkError,
            ) as exc:
                self._record_provider_error("Semantic Scholar", exc)
                logger.warning(
                    "[Research] Semantic Scholar unavailable for %r: %s",
                    query, exc,
                )
                break  # Network/timeout: no point retrying
            except (
                httpx.HTTPStatusError,
                ValueError,
            ) as exc:
                self._record_provider_error("Semantic Scholar", exc)
                logger.warning(
                    "[Research] Semantic Scholar returned an unusable response "
                    "for %r: %s",
                    query, exc,
                )
                break  # Non-retryable error
        return []

    # ======================================================
    # CROSSREF
    # ======================================================

    def _crossref_search(
        self, query: str, start_year: int = 2006, end_year: int = 2026,
        limit: int = 10,
    ) -> list[dict]:
        params = {
            "query.bibliographic": query,
            "rows": min(limit, 100),
            "filter": f"from-pub-date:{start_year},until-pub-date:{end_year}",
        }

        headers = {
            "User-Agent": (
                "ResearchOS/1.0 "
                "(mailto:researchos@example.com)"
            )
        }

        for attempt in range(self._MAX_RETRIES):
            try:
                with httpx.Client(
                    timeout=20.0,
                    headers=headers,
                ) as client:
                    response = client.get(
                        self.crossref_url,
                        params=params,
                    )

                if response.status_code == 429:
                    retry_after = self._get_retry_after(response)
                    backoff = max(retry_after, self._BASE_BACKOFF * (2 ** attempt))
                    logger.warning(
                        "[Research] Crossref rate limited (429) on attempt %d/%d, "
                        "retrying in %.1fs",
                        attempt + 1, self._MAX_RETRIES, backoff,
                    )
                    if attempt < self._MAX_RETRIES - 1:
                        time.sleep(backoff)
                        continue
                    self.provider_errors.setdefault(
                        "Crossref",
                        "rate limited after retries; try again later",
                    )
                    return []

                response.raise_for_status()

                data = response.json()

                results = []

                for item in (
                    data.get("message", {})
                    .get("items", [])
                ):
                    titles = item.get("title", [])

                    if not titles:
                        continue

                    title = titles[0]

                    authors = []

                    for author in item.get("author") or []:
                        name = (
                            f"{author.get('given', '')} "
                            f"{author.get('family', '')}"
                        ).strip()

                        if name:
                            authors.append(name)

                    year = None

                    date_info = (
                        item.get("published-print")
                        or item.get("published-online")
                        or item.get("issued")
                        or item.get("created")
                    )

                    if date_info:
                        parts = date_info.get(
                            "date-parts",
                            [],
                        )

                        if parts and parts[0]:
                            year = parts[0][0]

                    abstract = item.get(
                        "abstract",
                        "",
                    )

                    abstract = re.sub(
                        r"<[^>]+>",
                        " ",
                        abstract,
                    )

                    abstract = " ".join(
                        abstract.split()
                    )

                    # Crossref is-referenced-by-count ≈ citation count
                    citation_count = (
                        item.get("is-referenced-by-count") or 0
                    )

                    results.append(
                        {
                            "title": title,
                            "authors": authors,
                            "abstract": abstract,
                            "year": year,
                            "url": item.get("URL")
                            or (
                                f"https://doi.org/{item.get('DOI')}"
                                if item.get("DOI")
                                else ""
                            ),
                            "doi": item.get("DOI") or "",
                            "citation_count": citation_count,
                            "citation_source": "Crossref",
                            "google_scholar_verified": False,
                            "google_scholar_citations": None,
                            "venue": (
                                item.get(
                                    "container-title",
                                    [""],
                                )[0]
                                if item.get("container-title")
                                else ""
                            ),
                            "source": "Crossref",
                            "citations_available": citation_count > 0,
                        }
                    )

                return results

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
            ) as exc:
                self._record_provider_error("Crossref", exc)
                logger.warning(
                    "[Research] Crossref unavailable for %r: %s",
                    query, exc,
                )
                break  # Network/timeout: no point retrying
            except (
                httpx.HTTPStatusError,
                ValueError,
                TypeError,
            ) as exc:
                self._record_provider_error("Crossref", exc)
                logger.warning(
                    "[Research] Crossref returned an unusable response "
                    "for %r: %s",
                    query, exc,
                )
                break  # Non-retryable error
        return []

    # ======================================================
    # DUPLICATE REMOVAL
    # ======================================================

    def _remove_duplicates(
        self,
        papers: list[dict],
    ) -> list[dict]:

        seen = set()
        unique = []

        for paper in papers:
            title = paper.get(
                "title",
                "",
            )

            normalized = re.sub(
                r"[^a-z0-9]+",
                " ",
                title.lower(),
            ).strip()

            if not normalized:
                continue

            doi = (paper.get("doi") or "").strip().lower()
            if doi:
                dedupe_key = f"doi:{doi}"
            else:
                first_author = ""
                authors = paper.get("authors") or []
                if authors and isinstance(authors, list):
                    first_author = re.sub(r"[^a-z0-9]+", "", str(authors[0]).lower())
                year = paper.get("year") or ""
                dedupe_key = f"title:{normalized}|year:{year}|author:{first_author}"

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            unique.append(paper)

        return unique

    # ======================================================
    # CITATION-AWARE RELEVANCE RANKING
    # ======================================================

    def _rank_results(
        self,
        query: str,
        papers: list[dict],
    ) -> list[dict]:
        """Rank papers using a normalized citation-aware scoring model.

        Scoring components (total 100):
          - Citation Impact  (40 pts)  — normalized citation count
          - Topic Relevance  (30 pts)  — keyword overlap with query
          - Recency          (15 pts)  — how recent the paper is
          - Source Quality   (15 pts)  — venue, abstract availability
        """
        query_words = set(self._important_words(query))
        current_year = datetime.now().year

        # --- First pass: compute raw citation stats for normalisation ---
        citation_counts = [
            p.get("citation_count", 0) or 0 for p in papers
        ]
        max_citations = max(citation_counts) if citation_counts else 1
        # Use log-scale to avoid one mega-cited paper distorting everything
        log_max = math.log1p(max_citations) if max_citations > 0 else 1.0

        scored: list[dict] = []

        for paper in papers:
            title = (paper.get("title", "") or "").lower()
            abstract = (paper.get("abstract", "") or "").lower()
            venue = (paper.get("venue", "") or "").lower()
            year = paper.get("year") or current_year

            title_words = set(self._important_words(title))
            abstract_words = set(self._important_words(abstract))

            # ----- Component 1: Citation Impact (40 pts) -----
            raw_cite = paper.get("citation_count", 0) or 0
            cite_norm = (
                (math.log1p(raw_cite) / log_max) * 40
                if log_max > 0
                else 0
            )

            # ----- Component 2: Topic Relevance (30 pts) -----
            title_matches = query_words.intersection(title_words)
            abstract_matches = query_words.intersection(abstract_words)
            relevance = min(
                30,
                len(title_matches) * 6
                + len(abstract_matches) * 2,
            )
            # Bonus for exact phrase in title
            normalized_query = query.lower().strip()
            if normalized_query in title:
                relevance = min(30, relevance + 8)

            # ----- Component 3: Recency (15 pts) -----
            age = current_year - year if year else 20
            # Papers within 5 years get full score, linearly decay to 0 at 20 years
            recency = max(0, min(15, 15 * (1 - age / 20)))

            # ----- Component 4: Source Quality (15 pts) -----
            source = 0
            if venue:
                source += 5
            if abstract:
                source += 4
            if paper.get("doi"):
                source += 3
            if paper.get("citations_available"):
                source += 3
            source = min(15, source)

            total_score = cite_norm + relevance + recency + source
            score_100 = round(min(100, total_score))

            # Build score explanation
            if cite_norm >= 30:
                cite_label = "High"
            elif cite_norm >= 15:
                cite_label = "Medium"
            else:
                cite_label = "Low"

            if relevance >= 20:
                rel_label = "High"
            elif relevance >= 10:
                rel_label = "Medium"
            else:
                rel_label = "Low"

            if recency >= 10:
                rec_label = "High"
            elif recency >= 5:
                rec_label = "Medium"
            else:
                rec_label = "Low"

            paper_copy = dict(paper)
            paper_copy["relevance_score"] = score_100
            paper_copy["score_explanation"] = {
                "citation_impact": cite_label,
                "citations": raw_cite,
                "topic_relevance": rel_label,
                "recency": rec_label,
                "published": year,
                "source": paper.get("source", "Unknown"),
            }

            scored.append(paper_copy)

        # Sort by score descending, then citation count as tiebreaker
        scored.sort(
            key=lambda item: (
                item.get("relevance_score", 0),
                item.get("citation_count", 0),
            ),
            reverse=True,
        )

        return scored

    # ======================================================
    # TEXT PROCESSING
    # ======================================================

    def _important_words(
        self,
        text: str,
    ) -> list[str]:

        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "that",
            "this",
            "using",
            "based",
            "into",
            "through",
            "about",
            "research",
            "study",
            "system",
            "approach",
            "method",
            "methods",
        }

        words = re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )

        return [
            word
            for word in words
            if len(word) >= 3
            and word not in stop_words
        ]
