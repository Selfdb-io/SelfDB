"""
SelfDB Storage Service

Internal-only FastAPI service that stores file blobs under /app/data (storage_data volume)
and exposes minimal S3-like HTTP endpoints used by the backend proxy:
- POST   /api/v1/files/{bucket}/{path}
- GET    /api/v1/files/{bucket}/{path}
- HEAD   /api/v1/files/{bucket}/{path}
- DELETE /api/v1/files/{bucket}/{path}

Also supports bucket helpers:
- POST   /api/v1/buckets
- GET    /api/v1/buckets/{bucket}
- DELETE /api/v1/buckets/{bucket}
"""

import os
import shutil
import re
import mimetypes
from uuid import uuid4
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, JSONResponse
from pydantic import BaseModel

BASE_PATH = "/app/data"


def _ensure_base_dir():
    os.makedirs(BASE_PATH, exist_ok=True)


def _validate_bucket_name(bucket: str) -> bool:
    # Allow lowercase letters, digits, hyphens, and dots; must start/end alnum (S3-like)
    return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9\-\.]{1,61})[a-z0-9]", bucket))


def _validate_path(path: str) -> bool:
    if not path or path.startswith("/") or ".." in path or "\x00" in path:
        return False
    return True


def _safe_join(bucket: str, path: Optional[str] = None) -> str:
    # Prevent directory traversal
    full = os.path.normpath(os.path.join(BASE_PATH, bucket, path or ""))
    base = os.path.normpath(os.path.join(BASE_PATH, bucket))
    if not full.startswith(base):
        raise HTTPException(status_code=400, detail="Invalid path")
    return full


def _require_api_key(request: Request):
    configured = os.getenv("API_KEY")
    provided = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if configured and provided == configured:
        return True
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_API_KEY")


# Create FastAPI app
app = FastAPI(title="SelfDB Storage Service", version="1.0.0")

# Configure CORS (service-to-service only; backend calls with Docker DNS)
allowed_origins = os.getenv("ALLOWED_CORS")
if allowed_origins:
    allowed_origins = allowed_origins.split(",")
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str
    environment: Dict[str, Any]
    storage: Dict[str, Any]
    message: str


@app.get("/")
async def root():
    return {"message": "SelfDB Storage Service", "status": "ready"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    _ensure_base_dir()
    return HealthResponse(
        service="storage",
        status="ready",
        version= os.getenv("SELFDB_VERSION"),
        environment={
            "env": os.getenv("ENV"),
            "storage_port": int(os.getenv("STORAGE_PORT")),
            "api_key_configured": bool(os.getenv("API_KEY")),
        },
        storage={
            "type": "internal",
            "volume": "storage_data",
            "path": BASE_PATH,
        },
        message="Storage service is ready and configured",
    )


@app.get("/api/v1/storage/status")
async def storage_status():
    return {
        "service": "storage",
        "status": "ready",
        "capabilities": [
            "file_upload",
            "file_download",
            "bucket_management",
        ],
        "internal_only": True,
        "database_connected": True,
    }


# -------------------------
# Bucket helper endpoints
# -------------------------

class BucketCreate(BaseModel):
    name: str
    owner_id: Optional[str] = None
    public: Optional[bool] = False

class BucketUpdate(BaseModel):
    public: Optional[bool] = None


@app.post("/api/v1/buckets")
async def create_bucket(payload: BucketCreate, _: bool = Depends(_require_api_key)):
    name = payload.name.strip().lower()
    if not _validate_bucket_name(name):
        raise HTTPException(status_code=400, detail="Invalid bucket name")
    bucket_dir = _safe_join(name, "")
    os.makedirs(bucket_dir, exist_ok=True)
    return {
        "success": True,
        "bucket": {
            "name": name,
            "internal_bucket_name": name,
            "public": bool(payload.public),
        },
    }


@app.get("/api/v1/buckets")
async def list_buckets(_: bool = Depends(_require_api_key)):
    _ensure_base_dir()
    buckets = []
    if os.path.isdir(BASE_PATH):
        for entry in os.scandir(BASE_PATH):
            if entry.is_dir():
                name = entry.name
                if _validate_bucket_name(name):
                    buckets.append({
                        "name": name,
                        "internal_bucket_name": name,
                        "public": False,
                    })
    return {"success": True, "buckets": buckets, "total": len(buckets)}


@app.get("/api/v1/buckets/{bucket}")
async def get_bucket(bucket: str, _: bool = Depends(_require_api_key)):
    bucket = bucket.strip().lower()
    if not _validate_bucket_name(bucket):
        raise HTTPException(status_code=400, detail="Invalid bucket name")
    bucket_dir = _safe_join(bucket, "")
    if not os.path.isdir(bucket_dir):
        raise HTTPException(status_code=404, detail="Bucket not found")
    return {"success": True, "bucket": {"name": bucket}}


@app.delete("/api/v1/buckets/{bucket}")
async def delete_bucket(bucket: str, _: bool = Depends(_require_api_key)):
    bucket = bucket.strip().lower()
    if not _validate_bucket_name(bucket):
        raise HTTPException(status_code=400, detail="Invalid bucket name")
    bucket_dir = _safe_join(bucket, "")
    if not os.path.isdir(bucket_dir):
        raise HTTPException(status_code=404, detail="Bucket not found")

    # Recursively delete all files and subdirectories, then remove the bucket directory
    try:
        shutil.rmtree(bucket_dir)
    except FileNotFoundError:
        # If already removed by concurrent operation
        return {"success": True}
    except PermissionError:
        raise HTTPException(status_code=401, detail="Unauthorized to delete bucket")
    except Exception as e:
        raise HTTPException(status_code=503, detail="Failed to delete bucket")

    return {"success": True}


@app.put("/api/v1/buckets/{bucket}")
async def update_bucket(bucket: str, payload: BucketUpdate, _: bool = Depends(_require_api_key)):
    # For local filesystem backend we only acknowledge 'public' flag and return current info
    bucket = bucket.strip().lower()
    if not _validate_bucket_name(bucket):
        raise HTTPException(status_code=400, detail="Invalid bucket name")
    bucket_dir = _safe_join(bucket, "")
    if not os.path.isdir(bucket_dir):
        raise HTTPException(status_code=404, detail="Bucket not found")
    return {
        "success": True,
        "bucket": {
            "name": bucket,
            "internal_bucket_name": bucket,
            "public": bool(payload.public) if payload.public is not None else False,
        }
    }


@app.get("/api/v1/buckets/{bucket}/files")
async def list_bucket_files(bucket: str, _: bool = Depends(_require_api_key)):
    bucket = bucket.strip().lower()
    if not _validate_bucket_name(bucket):
        raise HTTPException(status_code=400, detail="Invalid bucket name")
    bucket_dir = _safe_join(bucket, "")
    if not os.path.isdir(bucket_dir):
        raise HTTPException(status_code=404, detail="Bucket not found")
    files = []
    for root, _, filenames in os.walk(bucket_dir):
        for fname in filenames:
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, bucket_dir)
            stat = os.stat(fpath)
            files.append({
                "id": rel_path,
                "filename": fname,
                "size": stat.st_size,
                "content_type": _guess_mime_type(fname),
                "created_at": int(stat.st_ctime),
                "updated_at": int(stat.st_mtime),
                "bucket": bucket,
            })
    return {"success": True, "files": files}


# -------------------------
# File endpoints
# -------------------------

def _guess_mime_type(filename: str) -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or "application/octet-stream"


@app.post("/api/v1/files/{bucket}/{path:path}")
async def upload_file(bucket: str, path: str, request: Request, _: bool = Depends(_require_api_key)):
    bucket = bucket.strip().lower()
    if not _validate_bucket_name(bucket) or not _validate_path(path):
        raise HTTPException(status_code=400, detail="Invalid bucket or path")

    body = await request.body()
    filename = request.headers.get("x-filename") or os.path.basename(path)
    ctype = request.headers.get("content-type") or _guess_mime_type(filename)

    # Ensure directories
    target_file = _safe_join(bucket, path)
    os.makedirs(os.path.dirname(target_file), exist_ok=True)

    with open(target_file, "wb") as f:
        f.write(body)

    return {
        "status": "success",
        "file_id": str(uuid4()),
        "size": len(body),
        "url": f"/api/v1/files/{bucket}/{path}",
    }


@app.get("/api/v1/files/{bucket}/{path:path}")
async def download_file(bucket: str, path: str, request: Request, _: bool = Depends(_require_api_key)):
    bucket = bucket.strip().lower()
    if not _validate_bucket_name(bucket) or not _validate_path(path):
        raise HTTPException(status_code=400, detail="Invalid bucket or path")

    file_path = _safe_join(bucket, path)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(file_path)
    filename = os.path.basename(file_path)
    content_type = _guess_mime_type(filename)

    # Handle Range requests
    range_header = request.headers.get("range")
    if range_header and range_header.startswith("bytes="):
        try:
            range_part = range_header.replace("bytes=", "")
            start_s, end_s = (range_part.split("-", 1) + [""])[:2]
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else file_size - 1
            if start < 0 or end < start or end >= file_size:
                raise ValueError()
        except Exception:
            return Response(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)

        def range_stream():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                chunk = 8192
                while remaining > 0:
                    data = f.read(min(chunk, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        headers = {
            "Content-Type": content_type,
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
        }
        return StreamingResponse(range_stream(), status_code=206, headers=headers)

    def full_stream():
        with open(file_path, "rb") as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                yield data

    headers = {
        "Content-Type": content_type,
        "Accept-Ranges": "bytes",
        "X-File-Name": filename,
    }
    return StreamingResponse(full_stream(), headers=headers)


@app.head("/api/v1/files/{bucket}/{path:path}")
async def head_file(bucket: str, path: str, _: bool = Depends(_require_api_key)):
    bucket = bucket.strip().lower()
    if not _validate_bucket_name(bucket) or not _validate_path(path):
        raise HTTPException(status_code=400, detail="Invalid bucket or path")

    file_path = _safe_join(bucket, path)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    filename = os.path.basename(file_path)
    content_type = _guess_mime_type(filename)
    size = os.path.getsize(file_path)

    return Response(status_code=200, headers={
        "Content-Type": content_type,
        "Content-Length": str(size),
        "X-File-Name": filename,
    })


@app.delete("/api/v1/files/{bucket}/{path:path}")
async def delete_file(bucket: str, path: str, _: bool = Depends(_require_api_key)):
    bucket = bucket.strip().lower()
    if not _validate_bucket_name(bucket) or not _validate_path(path):
        raise HTTPException(status_code=400, detail="Invalid bucket or path")

    file_path = _safe_join(bucket, path)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    os.remove(file_path)
    return {"status": "success"}


# Compatibility: backend.delete_file uses endpoint "/{bucket}/{path}"
@app.delete("/{bucket}/{path:path}")
async def delete_file_compat(bucket: str, path: str, _: bool = Depends(_require_api_key)):
    return await delete_file(bucket, path)  # Reuse logic


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("STORAGE_PORT"))
    uvicorn.run(app, host="0.0.0.0", port=port)