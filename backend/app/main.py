from fastapi import FastAPI
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.database.session import engine
from fastapi.middleware.cors import CORSMiddleware

from app.api.data_sources import router as data_sources_router
from app.api.chat import router as chat_router
from app.api.metadata import router as metadata_router



from app.api.intelligence import (
    router as intelligence_router,
)

from app.api.prompt_pipeline import (
    router as prompt_pipeline_router,
)

from app.api.query_plan import (
    router as query_plan_router,
)

from app.api.governance import (
    router as governance_router,
)

from app.api.executive_dashboard import (
    router as executive_dashboard_router,
)

from app.api.business_entities import (
    router as business_entities_router,
)

from app.api.business_relationships import (
    router as business_relationships_router,
)

from app.api.business_capabilities import (
    router as business_capabilities_router,
)

from app.api.reasoning import (
    router as reasoning_router,
)

from app.api.governed_query_plan import (
    router as governed_query_plan_router,
)

from app.api.business_join_mappings import (
    router as business_join_mappings_router,
)

from app.api.sql_compiler import (
    router as sql_compiler_router,
)

from app.api.business_rules import (
    router as business_rules_router,
)

from app.api.query_executor import (
    router as query_executor_router,
)


app = FastAPI(
    title="NibGPT API",
    description="Nib International Bank Enterprise AI Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://172.24.0.13:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




app.include_router(auth_router)
app.include_router(data_sources_router)
app.include_router(chat_router)
app.include_router(metadata_router)
app.include_router(intelligence_router)
app.include_router(prompt_pipeline_router)
app.include_router(query_plan_router)
app.include_router(governance_router)
app.include_router(executive_dashboard_router)
app.include_router(business_entities_router)
app.include_router(business_relationships_router)
app.include_router(business_capabilities_router)
app.include_router(reasoning_router)
app.include_router(governed_query_plan_router)
app.include_router(business_join_mappings_router)
app.include_router(sql_compiler_router)
app.include_router(business_rules_router)
app.include_router(query_executor_router)

@app.get("/")
def home():
    return {
        "application": "NIBGPT",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.get("/health/database")
def database_health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "database": "connected",
        "status": "healthy",
    }