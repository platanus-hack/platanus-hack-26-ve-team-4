from pydantic import BaseModel, ConfigDict, Field


class Order(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    order_id: str
    customer_id: str
    customer_email: str
    merchant: str
    status: str
    items: tuple[str, ...]
    total: int = Field(ge=0)
    refunded: int = Field(default=0, ge=0)


class KnowledgeArticle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str
    keywords: tuple[str, ...]
    answer: str


class SupportRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    customer_id: str = Field(min_length=1, max_length=40)
    order_id: str = Field(min_length=1, max_length=40)
    message: str = Field(min_length=1, max_length=4000)
    refund_amount: int | None = Field(default=None, ge=1)
    follow_up_seconds: int | None = Field(default=None, ge=1, le=1_209_600)
