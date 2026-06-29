"""Pydantic models: the note frontmatter contract and API payloads."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

NoteType = Literal[
    "preference", "habit", "research", "decision", "fact", "person", "project", "reference"
]
Tier = Literal["inbox", "longterm", "archived"]
Status = Literal["active", "archived", "merged"]
Review = Literal["pending", "elevated", "discarded", "merged"]


class NoteFrontmatter(BaseModel):
    """The YAML frontmatter block at the top of every note file."""

    id: str
    title: str
    type: NoteType
    tier: Tier = "inbox"
    status: Status = "active"
    tags: list[str] = Field(default_factory=list)
    created: str
    created_by: Optional[str] = None
    source_session: Optional[str] = None
    last_accessed: str
    access_count: int = 0
    confidence: Optional[float] = None
    review: Review = "pending"
    merged_into: Optional[str] = None
    links: list[str] = Field(default_factory=list)


class Note(BaseModel):
    """Frontmatter + markdown body."""

    frontmatter: NoteFrontmatter
    body: str = ""


class WriteRequest(BaseModel):
    title: str
    type: NoteType
    body: str = ""
    tags: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    tier: Tier = "inbox"
    confidence: Optional[float] = None
    created_by: Optional[str] = None
    source_session: Optional[str] = None


class LinkRequest(BaseModel):
    src: str
    dst: str
    rel: str = "relates_to"


class RecallHit(BaseModel):
    id: str
    title: str
    type: str
    tier: str
    snippet: str
    score: float


class ReviewItem(BaseModel):
    id: str
    title: str
    type: str
    confidence: Optional[float] = None
    created: str
    snippet: str


class PromoteRequest(BaseModel):
    id: str


class MergeRequest(BaseModel):
    ids: list[str]
    into: str


class DiscardRequest(BaseModel):
    id: str
