from dataclasses import dataclass, field
from enum import Enum


class KnowledgeDomain(str, Enum):
    PLATFORM = "platform"
    MARKETING = "marketing"
    PRODUCT = "product"
    BRAND = "brand"
    TREND = "trend"


@dataclass(frozen=True)
class KnowledgeEntry:
    id: str
    domain: KnowledgeDomain
    title: str
    summary: str
    content: str
    tags: list[str] = field(default_factory=list)
    verified_source: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class KnowledgeBundle:
    entries: list[KnowledgeEntry] = field(default_factory=list)

    def by_domain(self, domain: KnowledgeDomain) -> list[KnowledgeEntry]:
        return [e for e in self.entries if e.domain == domain]
