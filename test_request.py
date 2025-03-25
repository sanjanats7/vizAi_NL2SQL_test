from app.models.sql_models import TimeBasedQueriesUpdateRequest

test_payload = {
    "queries": [
        { "query_id": "79d4812c-345d-473e-a110-0fe56283ea94", "query": "SELECT * FROM orders WHERE order_date BETWEEN '2024-01-01' AND '2024-12-31';" },
        { "query_id": "09c43f20-1ed8-4a44-8cfd-be4fcdbef20d", "query": "SELECT SUM(price) FROM sales WHERE date BETWEEN '2024-01-01' AND '2024-12-31';" }
    ],
    "min_date": "2024-01-01",
    "max_date": "2024-12-31",
    "db_type": "postgres",
    "api_key": ""
}

try:
    parsed_data = TimeBasedQueriesUpdateRequest(**test_payload)
    print("✅ Pydantic Model Parsed Successfully:")
    print(parsed_data)
except Exception as e:
    print(f"❌ Error parsing Pydantic model: {str(e)}")
