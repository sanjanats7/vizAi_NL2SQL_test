from fastapi import APIRouter, HTTPException
from app.models.sql_models import QueriesForExecutorResponse
from app.services.query_generator import QueryGenerator,QueryRequest
from app.config import GOOGLE_API_KEY
import json

router = APIRouter()
@router.post("/", response_model=QueriesForExecutorResponse)
async def get_queries(request_data: QueryRequest):
    print(request_data)
    try:
        min_max_dates = [request_data.min_date, request_data.max_date]
        api_key = request_data.api_key or GOOGLE_API_KEY 
        if isinstance(request_data.db_schema, str):
            request_data.db_schema = json.loads(request_data.db_schema)
        schema_str = json.dumps(request_data.db_schema, indent=2) 

        # schema_str = format_schema(request_data.db_schema)  
        generator = QueryGenerator(
            # schema=request_data.schema,
            schema=schema_str,
            api_key=api_key,
            db_type=request_data.db_type
        )

        queries = generator.get_queries_for_executor(
            role=request_data.role,
            domain=request_data.domain,
            min_max_dates=min_max_dates
        )

        return QueriesForExecutorResponse(queries=queries)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
# class RequestData(BaseModel):
#     text: str

# @router.post("/test")
# async def test_service(data: RequestData):
#   return {"message": "data recieved."}
