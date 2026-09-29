from datetime import datetime; from typing import Literal; from fastapi import FastAPI, HTTPException; from pydantic import BaseModel, model_validator; from app.services.database import (get_variant, update_variant,);from app.services.ingestion import fetch_and_extract; from app.services.pipeline import process_post; from app.services.schedule import (SchedulingError, schedule_variant,); from app.services.publisher import (PublishingErrorpublish_variant,)


app = FastAPI(
    title="Social Media Studio",
    description="Content repurposing and publishing backend",
    version="1.0.0",
)

class PostCreate(BaseModel):
    source_type: Literal["markdown", "url"]

    content: str | None = None
    source_url: str | None = None

    @model_validator(mode="after")
    def validate_source(self):
        if self.source_type == "markdown":
            if not self.content or not self.content.strip():
                raise ValueError(
                    "content is required when source_type is 'markdown'."
                )

        if self.source_type == "url":
            if not self.source_url or not self.source_url.strip():
                raise ValueError(
                    "source_url is required when source_type is 'url'."
                )

        return self


class VariantEdit(BaseModel):
    content: str


class ScheduleCreate(BaseModel):
    scheduled_at: datetime


@app.post("/posts")
def create_post(post: PostCreate):

    if post.source_type == "markdown":

        return process_post(
            content=post.content,
            source_type="markdown",
        )

    if post.source_type == "url":

        try:
            extracted_content = fetch_and_extract(
                post.source_url
            )

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            )

        except RuntimeError as error:
            raise HTTPException(
                status_code=502,
                detail=str(error),
            )

        return process_post(
            content=extracted_content,
            source_type="url",
            source_url=post.source_url,
        )


@app.post("/variants/{variant_id}/approve")
def approve_variant(variant_id: int):

    variant = get_variant(variant_id)

    if variant is None:
        raise HTTPException(
            status_code=404,
            detail=f"Variant {variant_id} not found.",
        )

    if variant["status"] == "rejected":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Variant {variant_id} has been rejected "
                "and cannot be approved."
            ),
        )

    if variant["status"] == "approved":
        return {
            "id": variant_id,
            "status": "approved",
        }

    update_variant(
        variant_id=variant_id,
        status="approved",
    )

    return {
        "id": variant_id,
        "status": "approved",
    }


@app.put("/variants/{variant_id}")
def edit_variant(
    variant_id: int,
    variant: VariantEdit,
):

    existing_variant = get_variant(variant_id)

    if existing_variant is None:
        raise HTTPException(
            status_code=404,
            detail=f"Variant {variant_id} not found.",
        )

    if not variant.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Variant content cannot be empty.",
        )

    # Editing always returns the variant to draft.
    update_variant(
        variant_id=variant_id,
        content=variant.content,
        status="draft",
    )

    return {
        "id": variant_id,
        "status": "draft",
        "content": variant.content,
    }

@app.post("/variants/{variant_id}/reject")
def reject_variant(variant_id: int):

    variant = get_variant(variant_id)

    if variant is None:
        raise HTTPException(
            status_code=404,
            detail=f"Variant {variant_id} not found.",
        )

    if variant["status"] == "published":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Variant {variant_id} has already been "
                "published and cannot be rejected."
            ),
        )

    update_variant(
        variant_id=variant_id,
        status="rejected",
    )

    return {
        "id": variant_id,
        "status": "rejected",
    }


@app.post("/variants/{variant_id}/schedule")
def create_variant_schedule(
    variant_id: int,
    schedule: ScheduleCreate,
):

    try:
        schedule_id = schedule_variant(
            variant_id=variant_id,
            scheduled_at=schedule.scheduled_at,
        )

    except SchedulingError as error:

        message = str(error)

        # Missing variant → 404
        if "does not exist" in message:
            raise HTTPException(
                status_code=404,
                detail=message,
            )

        # Not approved → 409
        raise HTTPException(
            status_code=409,
            detail=message,
        )

    return {
        "schedule_id": schedule_id,
        "variant_id": variant_id,
        "scheduled_at": schedule.scheduled_at,
    }

@app.post("/variants/{variant_id}/publish")
def publish_variant_endpoint(
    variant_id: int,
):
    try:
        return publish_variant(
            variant_id=variant_id,
        )

    except PublishingError as error:
        message = str(error)

        if "does not exist" in message:
            raise HTTPException(
                status_code=404,
                detail=message,
            )

        raise HTTPException(
            status_code=409,
            detail=message,
        )