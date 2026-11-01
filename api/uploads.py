"""Bounded multipart uploads that never roll over to a disk file."""

from contextlib import asynccontextmanager

from fastapi import HTTPException, Request
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_POLICY_BYTES = 20 * 1024 * 1024
AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav"}


@asynccontextmanager
async def memory_form(request: Request, limit: int):
    """Cap the streamed request before parsing; permit only one in-memory file."""
    if request.headers.get("content-type", "").split(";", 1)[0].lower() != "multipart/form-data":
        raise HTTPException(400, "Please send a multipart upload")
    max_request = limit + 64 * 1024  # bounded space for form fields and multipart headers

    async def bounded_stream():
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > max_request:
                raise HTTPException(413, "Upload too large")
            yield chunk

    parser = MultiPartParser(request.headers, bounded_stream(), max_files=1, max_fields=4, max_part_size=4096)
    # Starlette normally spools files larger than 1 MiB to disk. The request cap is
    # lower than this parser's rollover threshold, including for chunked requests.
    parser.spool_max_size = max_request + 1
    try:
        form = await parser.parse()
    except MultiPartException:
        raise HTTPException(400, "Invalid multipart upload") from None
    try:
        yield form
    finally:
        await form.close()


async def read_file(form, field: str, limit: int, content_types: set[str]) -> tuple[bytes, str]:
    upload = form.get(field)
    if not isinstance(upload, UploadFile):
        raise HTTPException(422, f"Missing upload field: {field}")
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in content_types:
        raise HTTPException(400, "Unsupported upload type")
    content = await upload.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, "Upload too large")
    if not content:
        raise HTTPException(400, "Empty upload")
    return content, content_type
