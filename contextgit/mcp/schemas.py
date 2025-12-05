"""Pydantic schemas for MCP responses."""

from typing import List, Optional

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Define stub classes when pydantic is not available
    class BaseModel:  # type: ignore
        pass

    def Field(*args, **kwargs):  # type: ignore
        """Stub Field function that returns None."""
        return None


class RelevantFileNode(BaseModel):
    """Node relevant to a file."""
    id: str = Field(..., description="Node ID")
    type: str = Field(..., description="Node type")
    title: str = Field(..., description="Node title")
    file: str = Field(..., description="File path")
    distance: int = Field(..., description="Distance from target file")


class RelevantForFileResponse(BaseModel):
    """Response for relevant_for_file tool."""
    file: str = Field(..., description="Target file path")
    nodes: List[RelevantFileNode] = Field(default_factory=list, description="Relevant nodes")


class ExtractResponse(BaseModel):
    """Response for extract tool."""
    id: str = Field(..., description="Node ID")
    type: str = Field(..., description="Node type")
    title: str = Field(..., description="Node title")
    file: str = Field(..., description="Source file")
    snippet: str = Field(..., description="Extracted text content")


class StaleLink(BaseModel):
    """Stale link information."""
    from_id: str = Field(..., description="Source node ID")
    to_id: str = Field(..., description="Target node ID")
    relation_type: str = Field(..., description="Relationship type")
    sync_status: str = Field(..., description="Synchronization status")
    last_checked: Optional[str] = Field(None, description="Last check timestamp")


class StatusResponse(BaseModel):
    """Response for status tool."""
    total_nodes: int = Field(..., description="Total number of nodes")
    total_links: int = Field(..., description="Total number of links")
    stale_links: List[StaleLink] = Field(default_factory=list, description="Stale links")
    node_counts: dict = Field(default_factory=dict, description="Counts by node type")


class ImpactNode(BaseModel):
    """Node in impact analysis."""
    id: str = Field(..., description="Node ID")
    title: str = Field(..., description="Node title")
    type: str = Field(..., description="Node type")
    file: str = Field(..., description="File path")


class ImpactAnalysisResponse(BaseModel):
    """Response for impact_analysis tool."""
    requirement_id: str = Field(..., description="Target requirement ID")
    title: str = Field(..., description="Requirement title")
    type: str = Field(..., description="Requirement type")
    direct_downstream: List[ImpactNode] = Field(default_factory=list, description="Direct downstream nodes")
    indirect_downstream: List[ImpactNode] = Field(default_factory=list, description="Indirect downstream nodes")
    affected_files: List[str] = Field(default_factory=list, description="Files that may be affected")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested review actions")


class SearchResultNode(BaseModel):
    """Node in search results."""
    id: str = Field(..., description="Node ID")
    type: str = Field(..., description="Node type")
    title: str = Field(..., description="Node title")
    file: str = Field(..., description="File path")
    match_score: float = Field(..., description="Relevance score")


class SearchResponse(BaseModel):
    """Response for search tool."""
    query: str = Field(..., description="Search query")
    filters: dict = Field(default_factory=dict, description="Applied filters")
    results: List[SearchResultNode] = Field(default_factory=list, description="Matching nodes")
    total_matches: int = Field(..., description="Total number of matches")


class IndexNode(BaseModel):
    """Node in index."""
    id: str = Field(..., description="Node ID")
    type: str = Field(..., description="Node type")
    title: str = Field(..., description="Node title")
    file: str = Field(..., description="File path")
    status: str = Field(..., description="Node status")


class IndexLink(BaseModel):
    """Link in index."""
    from_id: str = Field(..., description="Source node ID")
    to_id: str = Field(..., description="Target node ID")
    relation_type: str = Field(..., description="Relationship type")
    sync_status: str = Field(..., description="Synchronization status")


class IndexResponse(BaseModel):
    """Response for index resource."""
    nodes: List[IndexNode] = Field(default_factory=list, description="All nodes in index")
    links: List[IndexLink] = Field(default_factory=list, description="All links in index")
    total_nodes: int = Field(..., description="Total number of nodes")
    total_links: int = Field(..., description="Total number of links")
