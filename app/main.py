from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.queries import router as api_router
from app.api.nl_to_sql import router as nl_to_sql_router
from app.api.time_based_update import router as time_based_query_update



app = FastAPI(
    title="SQL Query Generator API",
    description="API for generating insightful SQL queries using LLM",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/queries", tags=["Query Generation"])
app.include_router(nl_to_sql_router, prefix="/api/nlq", tags=["NLQ to SQL"])
app.include_router(time_based_query_update,prefix="/update_time_based_queries", tags=["Update queries based on time range"])


