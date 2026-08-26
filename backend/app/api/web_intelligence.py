from fastapi import (
    APIRouter,
)

from pydantic import (
    BaseModel,
    Field,
)

from app.ai.web_intelligence import (
    answer_nib_website_question,
)


router = APIRouter(
    prefix="/api/web-intelligence",
    tags=["NIBGPT Web Intelligence"],
)


class WebsiteQuestionRequest(
    BaseModel
):
    question: str = Field(
        min_length=2,
        max_length=5000,
    )


@router.post(
    "/nib-website/ask"
)
def ask_nib_website(
    payload: WebsiteQuestionRequest,
):
    return (
        answer_nib_website_question(
            payload.question
        )
    )