"""Storage repositories for recommendation candidates and product statistics."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Candidate:
    user_id: str
    rank: int
    product_id: int
    als_score: float


@dataclass(frozen=True)
class ProductStat:
    product_id: int
    category_code: str | None
    brand: str | None
    event_count: int
    unique_users: int
    average_price: float | None
    popularity_score: float = 0.0


@dataclass(frozen=True)
class SessionIntent:
    user_id: str
    user_session: str
    category_code: str
    intent_score: float


class BaseServingRepository(ABC):
    """Abstract interface isolating storage (Parquet, Cassandra, In-Memory) from serving logic."""

    @abstractmethod
    def get_candidates(self, user_id: str, limit: int = 50) -> list[Candidate]:
        """Fetch precomputed ALS candidates for a given user."""

    @abstractmethod
    def get_products(self, limit: int = 20) -> list[ProductStat]:
        """Fetch available products ordered by popularity."""

    @abstractmethod
    def get_product(self, product_id: int) -> ProductStat | None:
        """Fetch details for a single product."""

    @abstractmethod
    def get_session_intents(self, user_id: str, user_session: str | None = None) -> list[SessionIntent]:
        """Fetch real-time session intent scores."""

    @abstractmethod
    def is_healthy(self) -> tuple[bool, str]:
        """Return operational health status and descriptive message."""


class InMemoryServingRepository(BaseServingRepository):
    """In-memory repository used for fast unit tests and isolated fixtures."""

    def __init__(
        self,
        candidates: list[Candidate] | None = None,
        products: list[ProductStat] | None = None,
        session_intents: list[SessionIntent] | None = None,
    ) -> None:
        self._candidates: dict[str, list[Candidate]] = {}
        for c in candidates or []:
            self._candidates.setdefault(c.user_id, []).append(c)
        for u in self._candidates:
            self._candidates[u].sort(key=lambda x: (x.rank, -x.als_score))

        self._products: dict[int, ProductStat] = {p.product_id: p for p in (products or [])}
        self._session_intents: list[SessionIntent] = list(session_intents or [])

    def get_candidates(self, user_id: str, limit: int = 50) -> list[Candidate]:
        user_cands = self._candidates.get(user_id, [])
        return user_cands[:limit]

    def get_products(self, limit: int = 20) -> list[ProductStat]:
        # Return products ordered by popularity_score (descending)
        sorted_prods = sorted(self._products.values(), key=lambda p: (-p.popularity_score, -p.event_count, p.product_id))
        return sorted_prods[:limit]

    def get_product(self, product_id: int) -> ProductStat | None:
        return self._products.get(product_id)

    def get_session_intents(self, user_id: str, user_session: str | None = None) -> list[SessionIntent]:
        res = [s for s in self._session_intents if s.user_id == user_id]
        if user_session:
            res = [s for s in res if s.user_session == user_session]
        return res

    def is_healthy(self) -> tuple[bool, str]:
        return True, "in-memory repository healthy"


class ParquetServingRepository(BaseServingRepository):
    """File-backed repository loading generated Gold artifacts (Parquet) for local demo and testing."""

    def __init__(self, data_root: Path | str = "data/generated") -> None:
        self.data_root = Path(data_root)
        self.candidates_path = self.data_root / "gold" / "als_candidates"
        self.product_stats_path = self.data_root / "gold" / "product_stats"
        self._candidates_cache: dict[str, list[Candidate]] | None = None
        self._products_cache: dict[int, ProductStat] | None = None
        self._load_caches()

    def _load_caches(self) -> None:
        if not self.product_stats_path.exists() or not self.candidates_path.exists():
            return

        try:
            import pyarrow.parquet as pq

            # Load product stats
            p_table = pq.read_table(str(self.product_stats_path))
            products_dict: dict[int, ProductStat] = {}
            raw_products = p_table.to_pylist()
            max_events = max((r.get("event_count", 0) for r in raw_products), default=1)
            max_events = max(max_events, 1)

            for r in raw_products:
                pid = int(r["product_id"])
                ev_count = int(r.get("event_count", 0))
                pop_score = round(ev_count / max_events, 4)
                products_dict[pid] = ProductStat(
                    product_id=pid,
                    category_code=r.get("category_code"),
                    brand=r.get("brand"),
                    event_count=ev_count,
                    unique_users=int(r.get("unique_users", 0)),
                    average_price=float(r["average_price"]) if r.get("average_price") is not None else None,
                    popularity_score=pop_score,
                )
            self._products_cache = products_dict

            # Load candidates
            c_table = pq.read_table(str(self.candidates_path))
            candidates_dict: dict[str, list[Candidate]] = {}
            for r in c_table.to_pylist():
                uid = str(r["user_id"])
                c = Candidate(
                    user_id=uid,
                    rank=int(r["rank"]),
                    product_id=int(r["product_id"]),
                    als_score=float(r["als_score"]),
                )
                candidates_dict.setdefault(uid, []).append(c)

            for uid in candidates_dict:
                candidates_dict[uid].sort(key=lambda x: (x.rank, -x.als_score))
            self._candidates_cache = candidates_dict
        except Exception:
            # Leave caches as None or empty if loading fails
            self._products_cache = None
            self._candidates_cache = None

    def reload(self) -> None:
        self._load_caches()

    def get_candidates(self, user_id: str, limit: int = 50) -> list[Candidate]:
        if self._candidates_cache is None:
            self._load_caches()
        if not self._candidates_cache:
            return []
        return self._candidates_cache.get(user_id, [])[:limit]

    def get_products(self, limit: int = 20) -> list[ProductStat]:
        if self._products_cache is None:
            self._load_caches()
        if not self._products_cache:
            return []
        sorted_prods = sorted(self._products_cache.values(), key=lambda p: (-p.popularity_score, -p.event_count, p.product_id))
        return sorted_prods[:limit]

    def get_product(self, product_id: int) -> ProductStat | None:
        if self._products_cache is None:
            self._load_caches()
        if not self._products_cache:
            return None
        return self._products_cache.get(product_id)

    def get_session_intents(self, user_id: str, user_session: str | None = None) -> list[SessionIntent]:
        # Session intents in Wave 3 default to empty before streaming engine connects
        return []

    def is_healthy(self) -> tuple[bool, str]:
        if not self.candidates_path.exists() or not self.product_stats_path.exists():
            return False, f"Gold data paths missing in {self.data_root}"
        if self._products_cache is None or self._candidates_cache is None:
            self._load_caches()
        if self._products_cache is None or self._candidates_cache is None:
            return False, "Failed to parse Parquet gold data"
        return True, f"Parquet storage ready ({len(self._candidates_cache)} users, {len(self._products_cache)} products)"


class CassandraServingRepository(BaseServingRepository):
    """Cassandra-backed repository for live candidate retrieval and real-time session intent."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9042,
        keyspace: str = "ecommerce",
    ) -> None:
        self.host = host
        self.port = port
        self.keyspace = keyspace
        self._cluster = None
        self._session = None
        self._connect()

    def _connect(self) -> None:
        try:
            from cassandra.cluster import Cluster

            self._cluster = Cluster([self.host], port=self.port, connect_timeout=3.0)
            self._session = self._cluster.connect(self.keyspace)
        except Exception:
            self._cluster = None
            self._session = None

    def get_candidates(self, user_id: str, limit: int = 50) -> list[Candidate]:
        if self._session is None:
            self._connect()
        if self._session is None:
            return []
        try:
            stmt = self._session.prepare(
                "SELECT user_id, rank, product_id, als_score FROM recommendation_candidates WHERE user_id = ? LIMIT ?"
            )
            rows = self._session.execute(stmt, (user_id, limit))
            return [
                Candidate(
                    user_id=r.user_id,
                    rank=r.rank,
                    product_id=r.product_id,
                    als_score=r.als_score,
                )
                for r in rows
            ]
        except Exception:
            return []

    def get_products(self, limit: int = 20) -> list[ProductStat]:
        if self._session is None:
            self._connect()
        if self._session is None:
            return []
        try:
            rows = self._session.execute(
                "SELECT product_id, category_code, brand, event_count, unique_users, average_price, popularity_score FROM product_stats LIMIT 200"
            )
            prods = [
                ProductStat(
                    product_id=r.product_id,
                    category_code=r.category_code,
                    brand=r.brand,
                    event_count=r.event_count or 0,
                    unique_users=r.unique_users or 0,
                    average_price=r.average_price,
                    popularity_score=r.popularity_score or 0.0,
                )
                for r in rows
            ]
            prods.sort(key=lambda p: (-p.popularity_score, -p.event_count, p.product_id))
            return prods[:limit]
        except Exception:
            return []

    def get_product(self, product_id: int) -> ProductStat | None:
        if self._session is None:
            self._connect()
        if self._session is None:
            return None
        try:
            stmt = self._session.prepare(
                "SELECT product_id, category_code, brand, event_count, unique_users, average_price, popularity_score FROM product_stats WHERE product_id = ?"
            )
            row = self._session.execute(stmt, (product_id,)).one()
            if not row:
                return None
            return ProductStat(
                product_id=row.product_id,
                category_code=row.category_code,
                brand=row.brand,
                event_count=row.event_count or 0,
                unique_users=row.unique_users or 0,
                average_price=row.average_price,
                popularity_score=row.popularity_score or 0.0,
            )
        except Exception:
            return None

    def get_session_intents(self, user_id: str, user_session: str | None = None) -> list[SessionIntent]:
        if self._session is None:
            self._connect()
        if self._session is None:
            return []
        try:
            if user_session:
                stmt = self._session.prepare(
                    "SELECT user_id, user_session, category_code, intent_score FROM session_intent WHERE user_id = ? AND user_session = ?"
                )
                rows = self._session.execute(stmt, (user_id, user_session))
            else:
                stmt = self._session.prepare(
                    "SELECT user_id, user_session, category_code, intent_score FROM session_intent WHERE user_id = ? ALLOW FILTERING"
                )
                rows = self._session.execute(stmt, (user_id,))
            return [
                SessionIntent(
                    user_id=r.user_id,
                    user_session=r.user_session,
                    category_code=r.category_code,
                    intent_score=r.intent_score,
                )
                for r in rows
            ]
        except Exception:
            return []

    def is_healthy(self) -> tuple[bool, str]:
        if self._session is None:
            self._connect()
        if self._session is None:
            return False, f"Cannot connect to Cassandra at {self.host}:{self.port}"
        try:
            row = self._session.execute("SELECT release_version FROM system.local;").one()
            return True, f"Cassandra cluster online (v{row.release_version}, keyspace={self.keyspace})"
        except Exception as exc:
            return False, f"Cassandra query error: {exc}"


def resolve_serving_repository(
    storage_type: str | None = None,
    data_dir: Path | str = "data/generated",
    cassandra_host: str = "localhost",
    cassandra_port: int = 9042,
) -> BaseServingRepository:
    """Resolve active repository. Prefers Cassandra when healthy; falls back to Parquet."""
    if storage_type != "parquet":
        try:
            cassandra_repo = CassandraServingRepository(host=cassandra_host, port=cassandra_port)
            healthy, _ = cassandra_repo.is_healthy()
            if healthy:
                return cassandra_repo
        except Exception:
            pass

    return ParquetServingRepository(data_root=data_dir)

