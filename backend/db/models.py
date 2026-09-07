"""SQLAlchemy 2.0 ORM models for the harvested Dataverse metadata store.

Fully normalised: ``installation`` / ``dataverse`` / ``dataset`` entities, shared
lookup tables (``author`` / ``keyword`` / ``subject`` / ``publication``) with
junctions, and flat parent-keyed child tables for the free-text bags.

Column-length notes (MySQL, utf8mb4): parts of composite unique keys are kept
<= 191 chars so the 3072-byte index limit is never at risk; single-column unique
values stay <= 255.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# SQLite only auto-increments INTEGER PRIMARY KEY, not BIGINT; MySQL keeps BIGINT.
_BigPK = BigInteger().with_variant(Integer, "sqlite")


class Installation(Base):
    __tablename__ = "installation"

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    hostname: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column()
    lng: Mapped[float | None] = mapped_column()
    country: Mapped[str | None] = mapped_column(String(191), index=True)
    launch_year: Mapped[int | None] = mapped_column(Integer)
    doi_authority: Mapped[str | None] = mapped_column(String(255))
    dv_hub_id: Mapped[str | None] = mapped_column(String(255))
    metrics: Mapped[bool | None] = mapped_column(Boolean)


class Dataverse(Base):
    __tablename__ = "dataverse"
    __table_args__ = (
        UniqueConstraint("installation_id", "identifier", name="uq_dataverse_natural"),
    )

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("installation.id"), index=True
    )
    identifier: Mapped[str] = mapped_column(String(191))
    name: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    affiliation: Mapped[str | None] = mapped_column(String(512))
    parent_dataverse_identifier: Mapped[str | None] = mapped_column(String(191), index=True)
    image_url: Mapped[str | None] = mapped_column(String(1024))
    dataset_count: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1")
    )


class Dataset(Base):
    __tablename__ = "dataset"
    __table_args__ = (
        UniqueConstraint("installation_id", "natural_key", name="uq_dataset_natural"),
    )

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("installation.id"), index=True
    )
    dataverse_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataverse.id"), index=True
    )
    parent_dataverse_identifier: Mapped[str | None] = mapped_column(
        String(191), index=True
    )
    global_id: Mapped[str | None] = mapped_column(String(255))
    identifier: Mapped[str | None] = mapped_column(String(255))
    natural_key: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    publisher: Mapped[str | None] = mapped_column(String(512))
    citation: Mapped[str | None] = mapped_column(Text)
    citation_html: Mapped[str | None] = mapped_column(Text)
    storage_identifier: Mapped[str | None] = mapped_column(String(512))
    file_count: Mapped[int | None] = mapped_column(Integer)
    version_id: Mapped[int | None] = mapped_column(BigInteger)
    version_state: Mapped[str | None] = mapped_column(String(64))
    major_version: Mapped[int | None] = mapped_column(Integer)
    minor_version: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1")
    )

    authors: Mapped[list[DatasetAuthor]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class Author(Base):
    __tablename__ = "author"
    __table_args__ = (
        UniqueConstraint(
            "name_norm", "affiliation_norm", "identifier", name="uq_author_natural"
        ),
    )

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(512))
    affiliation: Mapped[str | None] = mapped_column(String(512))
    identifier: Mapped[str] = mapped_column(String(191), default="")
    name_norm: Mapped[str] = mapped_column(String(191), default="")
    affiliation_norm: Mapped[str] = mapped_column(String(191), default="")


class Keyword(Base):
    __tablename__ = "keyword"

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    term: Mapped[str | None] = mapped_column(String(512))
    term_norm: Mapped[str] = mapped_column(String(255), unique=True)


class Subject(Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(255), unique=True)


class Publication(Base):
    __tablename__ = "publication"
    __table_args__ = (
        UniqueConstraint("url", "id_number", "citation_norm", name="uq_publication_natural"),
    )

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    citation: Mapped[str | None] = mapped_column(Text)
    citation_norm: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(String(255), default="")
    id_type: Mapped[str | None] = mapped_column(String(64))
    id_number: Mapped[str] = mapped_column(String(128), default="")


class DatasetAuthor(Base):
    __tablename__ = "dataset_author"

    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("author.id"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, default=0)


class DatasetKeyword(Base):
    __tablename__ = "dataset_keyword"

    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), primary_key=True
    )
    keyword_id: Mapped[int] = mapped_column(
        ForeignKey("keyword.id"), primary_key=True
    )


class DatasetSubject(Base):
    __tablename__ = "dataset_subject"

    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), primary_key=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subject.id"), primary_key=True
    )


class DatasetPublication(Base):
    __tablename__ = "dataset_publication"

    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), primary_key=True
    )
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("publication.id"), primary_key=True
    )


class DatasetContact(Base):
    __tablename__ = "dataset_contact"

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(512))
    affiliation: Mapped[str | None] = mapped_column(String(512))


class DatasetProducer(Base):
    __tablename__ = "dataset_producer"

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(512))
    affiliation: Mapped[str | None] = mapped_column(String(512))


class DatasetRelatedMaterial(Base):
    __tablename__ = "dataset_related_material"

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str | None] = mapped_column(Text)


class DatasetDataSource(Base):
    __tablename__ = "dataset_data_source"

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str | None] = mapped_column(Text)


class DatasetGeographicCoverage(Base):
    __tablename__ = "dataset_geographic_coverage"

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), index=True
    )
    coverage: Mapped[str | None] = mapped_column(String(512))


class DatasetPublicationStatus(Base):
    __tablename__ = "dataset_publication_status"

    id: Mapped[int] = mapped_column(_BigPK, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str | None] = mapped_column(String(64))


class PullState(Base):
    """Per-installation harvest watermark (replaces data/state/last_pull.json)."""

    __tablename__ = "pull_state"

    installation_id: Mapped[int] = mapped_column(
        ForeignKey("installation.id"), primary_key=True
    )
    last_pulled_at: Mapped[datetime | None] = mapped_column(DateTime)
