from dataclasses import dataclass, field
from datetime import date


@dataclass
class FileMetadata:
    """归档文件的元数据信息"""
    path: str
    title: str
    tags: list[str] = field(default_factory=list)
    category: str = "inbox"
    project: str | None = None
    created_at: str = ""
    summary: str = ""
    original_title: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "title": self.title,
            "tags": self.tags,
            "category": self.category,
            "project": self.project,
            "created_at": self.created_at,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileMetadata":
        return cls(
            path=data["path"],
            title=data["title"],
            tags=data.get("tags", []),
            category=data.get("category", "inbox"),
            project=data.get("project"),
            created_at=data.get("created_at", ""),
            summary=data.get("summary", ""),
        )


@dataclass
class IndexEntry:
    """全局索引条目"""
    path: str
    title: str
    tags: list[str] = field(default_factory=list)
    category: str = "inbox"
    project: str | None = None
    created_at: str = ""
    summary: str = ""
    file_type: str = "md"

    def to_dict(self) -> dict:
        return {
            "path": self.path.replace("\\", "/"),
            "title": self.title,
            "tags": self.tags,
            "category": self.category,
            "project": self.project,
            "created_at": self.created_at,
            "summary": self.summary,
            "file_type": self.file_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IndexEntry":
        return cls(
            path=data["path"].replace("\\", "/"),
            title=data["title"],
            tags=data.get("tags", []),
            category=data.get("category", "inbox"),
            project=data.get("project"),
            created_at=data.get("created_at", ""),
            summary=data.get("summary", ""),
            file_type=data.get("file_type", "md"),
        )


@dataclass
class ProjectEntry:
    """单个项目的映射条目"""
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "files": self.files,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectEntry":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            files=data.get("files", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class ProjectMap:
    """跨文件夹的项目视图索引，解决不同文件夹文档属于同一项目的问题"""
    version: int = 1
    projects: dict[str, ProjectEntry] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "projects": {k: v.to_dict() for k, v in self.projects.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectMap":
        projects = {}
        for key, entry_data in data.get("projects", {}).items():
            projects[key] = ProjectEntry.from_dict(entry_data)
        return cls(
            version=data.get("version", 1),
            projects=projects,
        )
