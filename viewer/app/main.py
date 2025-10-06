# Deprecated module
#
# This file previously hosted a FastAPI app to serve a custom UI.
# The project has been simplified to use only InfluxDB's built-in UI.
#
# The active ingestion process is in `runner.py`, which starts
# `MQTTInfluxIngestor` from `ingestor.py`.

if __name__ == "__main__":
    print("viewer.app.main is deprecated. Use runner.py to start the ingestor.")
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import os
from datetime import datetime, timedelta, timezone

from influxdb_client import InfluxDBClient

import config
from ingestor import MQTTInfluxIngestor

app = FastAPI(title="OBD Viewer")

# Static frontend
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
STATIC_DIR = os.path.abspath(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def index_page():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Start the MQTT ingestor on app startup
_ingestor: MQTTInfluxIngestor | None = None

@app.on_event("startup")
async def startup_event():
    global _ingestor
    _ingestor = MQTTInfluxIngestor()
    _ingestor.start()

@app.on_event("shutdown")
async def shutdown_event():
    global _ingestor
    if _ingestor:
        _ingestor.stop()


def _influx_query_api():
    client = InfluxDBClient(url=config.INFLUX_URL, token=config.INFLUX_TOKEN, org=config.INFLUX_ORG)
    return client, client.query_api()

@app.get("/api/series")
async def list_series(hours: int = Query(default=config.DEFAULT_QUERY_HOURS, ge=1, le=168)) -> List[str]:
    client, q = _influx_query_api()
    try:
        start = f"-{hours}h"
        flux = f"""
        import "influxdata/influxdb/schema"
        from(bucket: "{config.INFLUX_BUCKET}")
            |> range(start: {start})
            |> filter(fn: (r) => r._measurement == "obd")
            |> group()
            |> distinct(column: "key")
            |> keep(columns: ["key"])
        """
        tables = q.query(flux)
        keys: set[str] = set()
        for table in tables:
            for row in table.records:
                k = row.values.get("key")
                if k:
                    keys.add(k)
        return sorted(list(keys))
    finally:
        client.close()

@app.get("/api/data")
async def get_data(
    keys: List[str] = Query(default=[]),
    start_ms: int = Query(..., description="Start time (epoch ms)"),
    end_ms: int = Query(..., description="End time (epoch ms)"),
) -> Dict[str, List[Dict[str, int]]]:
    if not keys:
        return {}

    start_ns = start_ms * 1_000_000
    end_ns = end_ms * 1_000_000

    client, q = _influx_query_api()
    try:
        keys_set = set(keys)
        # Build Flux query filtering by keys
        keys_filter = " or ".join([f'r.key == "{k}"' for k in keys_set])
        flux = f"""
        from(bucket: "{config.INFLUX_BUCKET}")
            |> range(start: time(v: {start_ns}ns), stop: time(v: {end_ns}ns))
            |> filter(fn: (r) => r._measurement == "obd" and ({keys_filter}))
            |> keep(columns: ["_time", "_value", "key"]) 
            |> sort(columns: ["key", "_time"]) 
        """
        tables = q.query(flux)
        result: Dict[str, List[Dict[str, int]]] = {k: [] for k in keys_set}
        for table in tables:
            for row in table.records:
                k = row.values.get("key")
                v = row.get_value()
                t = row.get_time()
                if k in result and isinstance(v, (int, float)):
                    # Ensure integers
                    result[k].append({"ts": int(t.timestamp() * 1000), "v": int(v)})
        return result
    finally:
        client.close()
