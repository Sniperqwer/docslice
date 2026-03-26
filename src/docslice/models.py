"""Core data models for docslice blueprints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class TocNode(BaseModel):
    title: str
    url: str | None = None
    children: list["TocNode"] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be empty")
        return title


class Config(BaseModel):
    toc_selector: str | None = None
    content_selector: str | None = None
    delay: float = 1.5

    @field_validator("delay")
    @classmethod
    def validate_delay(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("delay must be greater than 0")
        return value


class Blueprint(BaseModel):
    version: int = 1
    project_name: str
    base_url: str
    generated_from: str | None = None
    config: Config = Field(default_factory=Config)
    toc: list[TocNode]

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("version must be 1")
        return value

    @field_validator("project_name", "base_url")
    @classmethod
    def validate_required_string(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("value must not be empty")
        return text

    @field_validator("toc")
    @classmethod
    def validate_toc(cls, value: list[TocNode]) -> list[TocNode]:
        if not value:
            raise ValueError("toc must not be empty")
        return value

