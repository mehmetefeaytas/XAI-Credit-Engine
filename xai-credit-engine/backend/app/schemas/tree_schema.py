"""
app/schemas/tree_schema.py
──────────────────────────────────────────────────────────────────────────────
Ağaç yapısı API Pydantic şemaları.
"""

from pydantic import BaseModel, Field


class TreeBuildRequest(BaseModel):
    """POST /tree/build isteği."""
    max_depth:         int   = Field(default=8,     ge=1, le=20)
    min_samples_split: int   = Field(default=5,     ge=2, le=1000)
    min_samples_leaf:  int   = Field(default=2,     ge=1, le=500)
    use_gain_ratio:    bool  = Field(default=False)
    description:       str   = Field(default="",    max_length=200)

    model_config = {"json_schema_extra": {"example": {
        "max_depth": 8, "min_samples_split": 5, "use_gain_ratio": False
    }}}


class NodeResponse(BaseModel):
    """Tek ağaç düğümü çıktısı."""
    id:           str
    feature_name: str | None
    threshold:    float | None
    operator:     str | None
    is_leaf:      bool
    leaf_label:   str | None
    depth:        int
    entropy:      float
    sample_count: int


class EdgeResponse(BaseModel):
    """Tek kenar çıktısı."""
    id:             str
    source_node_id: str
    target_node_id: str
    branch_value:   bool


class FeatureImportanceItem(BaseModel):
    """Özellik bilgi kazancı skoru."""
    feature: str
    score:   float
    rank:    int


class TreeBuildResponse(BaseModel):
    """POST /tree/build çıktısı."""
    version_id:          str
    built_at:            str
    total_nodes:         int
    leaf_nodes:          int
    inner_nodes:         int
    max_depth_reached:   int
    training_size:       int
    is_valid:            bool
    validation_errors:   list[str]
    feature_importance:  list[FeatureImportanceItem]
    root_node_id:        str
    nodes:               list[NodeResponse]
    edges:               list[EdgeResponse]


class TreeListItem(BaseModel):
    """Ağaç listesi tek öğesi."""
    version_id:    str
    built_at:      str
    total_nodes:   int
    is_active:     bool
    training_size: int
    description:   str
