"""Opaque, job-owned production files and additive material-row compatibility."""
from contextlib import closing
import os
import re
import time
import unicodedata
import uuid
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.formparsers import MultiPartException

MAX_ATTACHMENT_BYTES = 104857600
CHUNK_BYTES = 1024 * 1024
MAX_REQUEST_BYTES = MAX_ATTACHMENT_BYTES + CHUNK_BYTES
FILE_ID = re.compile(r'[0-9a-f]{32}')
ROW_ID = re.compile(r'[A-Za-z0-9_-]{1,128}')


class _BodyLimitExceeded(MultiPartException):
    """Multipart parsers close temporary files when this exception interrupts them."""


class AttachmentBodyLimit:
    """Bound multipart reads before FastAPI can spool an unbounded upload."""
    def __init__(self, app, prefix):
        self.app = app
        self.path = re.compile(re.escape(prefix) + r'/api/[^/]+/attachments')

    async def __call__(self, scope, receive, send):
        if (scope['type'] != 'http' or scope.get('method') != 'POST'
                or not self.path.fullmatch(scope.get('path', ''))):
            return await self.app(scope, receive, send)
        response = JSONResponse({'detail': 'upload request too large (100 MB file max)'}, status_code=413)
        for name, value in scope.get('headers', []):
            if name.lower() == b'content-length':
                try:
                    if int(value) > MAX_REQUEST_BYTES:
                        return await response(scope, receive, send)
                except ValueError:
                    pass  # The actual stream is bounded regardless of its declared length.
        received = 0
        exceeded = False

        async def bounded_receive():
            nonlocal received, exceeded
            message = await receive()
            if message['type'] == 'http.request':
                received += len(message.get('body', b''))
                if received > MAX_REQUEST_BYTES:
                    exceeded = True
                    raise _BodyLimitExceeded('attachment request too large')
            return message

        async def guarded_send(message):
            # Request parsing can convert MultiPartException into a 400 response.
            # Suppress that response and use the size-specific 413 after cleanup.
            if not exceeded:
                await send(message)

        try:
            await self.app(scope, bounded_receive, guarded_send)
        except _BodyLimitExceeded:
            pass
        if exceeded:
            await response(scope, receive, send)


def init_db(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS attachments (
        id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        name TEXT NOT NULL,
        size INTEGER NOT NULL,
        storage_name TEXT NOT NULL UNIQUE,
        created_at REAL NOT NULL
    )''')


def display_filename(raw):
    """A filename may describe a file, but never choose its storage path."""
    name = re.split(r'[/\\]', raw or '')[-1]
    name = ''.join(char for char in name if not unicodedata.category(char).startswith('C'))
    return name.strip(' .')[:200] or 'attachment'


def find_file(conn, job_id, file_id):
    if not isinstance(file_id, str) or not FILE_ID.fullmatch(file_id):
        return None
    return conn.execute('SELECT * FROM attachments WHERE id=? AND job_id=?',
                        (file_id, job_id)).fetchone()


def file_metadata(row, prefix):
    return {'id': row['id'], 'name': row['name'], 'size': row['size'],
            'url': f"{prefix}/api/{row['job_id']}/attachments/{row['id']}"}


async def store_file(upload, job_id, directory, connect, prefix):
    directory = Path(directory)
    try:
        directory.mkdir(mode=0o750)
    except FileExistsError:
        pass
    else:
        directory.chmod(0o750)
    file_id = uuid.uuid4().hex
    path = directory / file_id
    created = False
    try:
        size = 0
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as target:
            created = True
            while True:
                chunk = await upload.read(CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_ATTACHMENT_BYTES:
                    raise HTTPException(413, 'file too large (100 MB max)')
                target.write(chunk)
        name = display_filename(upload.filename)
        with closing(connect()) as conn, conn:
            conn.execute('INSERT INTO attachments (id,job_id,name,size,storage_name,created_at) VALUES (?,?,?,?,?,?)',
                         (file_id, job_id, name, size, file_id, time.time()))
            row = find_file(conn, job_id, file_id)
        return file_metadata(row, prefix)
    except BaseException:
        # A failed/cancelled upload owns only this new path. Never erase versions
        # already returned to callers, including the vanishingly rare ID collision.
        if created:
            path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def _attachment_ids(value, baseline=False):
    """Normalize old single-file values and new ordered lists for comparisons."""
    if value is None:
        return []
    entries = value if isinstance(value, list) else [value]
    ids = entries if baseline else [entry.get('id') if isinstance(entry, dict) else None
                                    for entry in entries]
    if (any(not isinstance(file_id, str) or not FILE_ID.fullmatch(file_id) for file_id in ids)
            or len(set(ids)) != len(ids)):
        detail = 'Invalid material attachment baseline.' if baseline else 'Invalid attachment for this ticket.'
        raise HTTPException(400, detail)
    return ids


def prepare_material_fields(state, previous, conn, job_id, prefix):
    """Validate new clients and preserve old-client saves only when rows are certain."""
    fields = ('materialRowIds', 'materialFiles')
    base_supplied = 'materialFileBase' in state
    baseline = state.pop('materialFileBase', None)
    explicit = [field in state for field in fields]
    if any(explicit):
        materials = state.get('materials')
        row_ids, files = state.get(fields[0]), state.get(fields[1])
        if (not all(explicit) or not isinstance(materials, list)
                or not isinstance(row_ids, list) or not isinstance(files, list)
                or len(row_ids) != len(materials) or len(files) != len(materials)):
            raise HTTPException(400, 'Material row IDs and files must align with materials.')
        if (any(not isinstance(value, str) or not ROW_ID.fullmatch(value) for value in row_ids)
                or len(set(row_ids)) != len(row_ids)):
            raise HTTPException(400, 'Material row IDs must be unique, nonempty identifiers.')
        if base_supplied:
            if (not isinstance(baseline, dict)
                    or any(not isinstance(key, str) or not ROW_ID.fullmatch(key) for key in baseline)):
                raise HTTPException(400, 'Invalid material attachment baseline.')
            baseline = {key: _attachment_ids(value, baseline=True) for key, value in baseline.items()}
        old_rows = dict(zip((previous or {}).get('materialRowIds', []),
                            (previous or {}).get('materialFiles', [])))
        old_ids = {row_id: _attachment_ids(files) for row_id, files in old_rows.items()}
        if any(old_ids.values()) and not base_supplied:
            raise HTTPException(409, 'Material attachments changed. Reload the ticket before saving.')
        if base_supplied:
            for row_id, current in old_ids.items():
                if baseline.get(row_id, []) != current:
                    raise HTTPException(409, 'Material attachments changed. Reload the ticket before saving.')
            if any(row_id not in old_rows and baseline.get(row_id, []) for row_id in row_ids):
                raise HTTPException(409, 'Material attachments changed. Reload the ticket before saving.')
        canonical = []
        for value in files:
            row_files = []
            for file_id in _attachment_ids(value):
                row = find_file(conn, job_id, file_id)
                if row is None:
                    raise HTTPException(400, 'Invalid attachment for this ticket.')
                row_files.append(file_metadata(row, prefix))
            # An old tab can still save a single file without rewriting its shape.
            canonical.append(row_files if isinstance(value, list) else row_files[0] if row_files else None)
        state['materialFiles'] = canonical
        return

    if not previous or not any(field in previous for field in fields):
        return
    # Existing materialDetails/completion omission handling runs first. Comparing
    # all three arrays also catches duplicate-name swaps and changed row meaning.
    unchanged = all(state.get(field) == previous.get(field)
                    for field in ('materials', 'materialDetails', 'materialCompleted'))
    has_files = any(_attachment_ids(files) for files in previous.get('materialFiles', []))
    if has_files and not unchanged:
        raise HTTPException(409, 'This ticket has material attachments. Reload the updated editor before changing material rows.')
    if unchanged:
        for field in fields:
            if field in previous:
                state[field] = previous[field]
    # An old editor may still change unattached rows. Do not retain IDs/metadata
    # by index after that change; the new editor will assign fresh row IDs.
