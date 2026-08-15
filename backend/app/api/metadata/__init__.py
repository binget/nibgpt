from fastapi import APIRouter

from app.api.metadata.explorer import (
    router as explorer_router,
)
from app.api.metadata.generator import (
    router as generator_router,
)
from app.api.metadata.updates import (
    router as updates_router,
)

from app.api.metadata.knowledge import (
    router as knowledge_router,
)


router = APIRouter(
    prefix="/api/metadata",
    tags=["Metadata Catalogue"],
)

router.include_router(explorer_router)
router.include_router(updates_router)
router.include_router(generator_router)
router.include_router(knowledge_router)
