import enum

from sqlalchemy import (
    Boolean,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class Modality(enum.Enum):
    """Represents the different modalities a model can support."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class ProviderModel(Base):
    """
    Association table linking Providers and Models.

    Represents the specific offering of a Model by a Provider, including
    pricing, capabilities, and the API-specific model name.
    """

    __tablename__ = "provider_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"))

    api_model_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    context_window: Mapped[int] = mapped_column(Integer)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_cost_per_mtok: Mapped[float] = mapped_column(Float)
    cached_input_cost_per_mtok: Mapped[float | None] = mapped_column(Float, nullable=True)  # NEW FIELD
    output_cost_per_mtok: Mapped[float] = mapped_column(Float)
    tokens_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False)
    discount_start_time_utc: Mapped[str] = mapped_column(String(5), default="00:00", nullable=True)
    discount_end_time_utc: Mapped[str] = mapped_column(String(5), default="00:00", nullable=True)
    input_discount_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=True)
    output_discount_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    provider: Mapped["Provider"] = relationship(back_populates="model_offerings")
    model: Mapped["Model"] = relationship(back_populates="provider_offerings")
    modalities_association: Mapped[list["ProviderModelModality"]] = relationship(
        cascade="all, delete-orphan"
    )
    modalities: Mapped[list[Modality]] = association_proxy("modalities_association", "modality")

    __table_args__ = (UniqueConstraint("provider_id", "model_id", name="_provider_model_uc"),)

    def __repr__(self) -> str:
        return f"<ProviderModel(api_model_name='{self.api_model_name}')>"


class ProviderModelModality(Base):
    """Association object between ProviderModel and Modality."""

    __tablename__ = "provider_model_modalities"

    provider_model_id: Mapped[int] = mapped_column(
        ForeignKey("provider_models.id"), primary_key=True
    )
    modality: Mapped[Modality] = mapped_column(SqlEnum(Modality), primary_key=True)


class Provider(Base):
    """
    Represents an API provider like OpenAI, Anthropic, AWS Bedrock, etc.
    """

    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    api_key_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str] = mapped_column(String(255))

    model_offerings: Mapped[list["ProviderModel"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Provider(id={self.id}, name='{self.name}')>"


class Model(Base):
    """
    Represents a conceptual model, independent of any single provider.
    e.g., "Claude 3 Opus"
    """

    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    provider_offerings: Mapped[list["ProviderModel"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )


    def __repr__(self) -> str:
        return f"<Model(id={self.id}, model_name='{self.model_name}')>"
