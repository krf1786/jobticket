"""Real HTTP routes and isolated SQLite/files; no production access or storage mocks."""
import asyncio
import copy
import io
import json
import os
import stat
from html.parser import HTMLParser
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi import UploadFile

from test_backend import load_isolated_backend


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        connections = []
        original_connect = sqlite3.connect
        def connect(*args, **kwargs):
            kwargs['check_same_thread'] = False
            conn = original_connect(*args, **kwargs)
            connections.append(conn)
            return conn
        connection_patch = patch.object(sqlite3, 'connect', connect)
        connection_patch.start()
        self.addCleanup(connection_patch.stop)
        self.addCleanup(lambda: [conn.close() for conn in connections])
        self.app = load_isolated_backend(self.root)
        self.base = {'jobName': 'TEST01 synthetic', 'materials': ['Acrylic', 'Acrylic'],
                     'materialDetails': ['First cut', 'Second cut'],
                     'materialCompleted': [False, True], 'notes': '', 'image': None}
        self.assertEqual(self.put(self.base).status_code, 200)

    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app.app),
                                         base_url='http://testserver') as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(send())

    def put(self, state, job='TEST01'):
        return self.request('PUT', '/jobticket/api/' + job, json=state)

    def ticket(self, job='TEST01'):
        return self.request('GET', '/jobticket/api/' + job).json()

    def upload(self, content=b'PDF\x00\xff original bytes', name='cut.ai', job='TEST01'):
        return self.request('POST', '/jobticket/api/' + job + '/attachments',
                            files={'file': (name, content, 'application/postscript')})

    def attached(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.text)
        file = response.json()['file']
        state = dict(self.base, materialRowIds=['row-first', 'row-second'], materialFiles=[file, None])
        self.assertEqual(self.put(state).status_code, 200)
        state['materialFileBase'] = {'row-first': file['id'], 'row-second': None}
        return state, file

    def stored_files(self):
        root = self.root / 'attachments'
        return sorted(path.name for path in root.iterdir()) if root.exists() else []

    def test_explicit_attachment_arrays_are_validated_on_new_tickets(self):
        before = self.ticket()
        response = self.put(dict(self.base, materialRowIds=['duplicate', 'duplicate'], materialFiles=[None, None]))
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.ticket(), before)
        response = self.put(dict(self.base, materialRowIds=['row-first', 'row-second']))
        self.assertEqual(response.status_code, 400, response.text)

    def test_upload_download_original_bytes_and_safe_headers(self):
        response = self.upload(name='../../folder\\cut one.ai', job='test01')
        self.assertEqual(response.status_code, 200, response.text)
        file = response.json()['file']
        self.assertRegex(file['id'], r'^[0-9a-f]{32}$')
        self.assertEqual(file, {'id': file['id'], 'name': 'cut one.ai', 'size': 20,
                                'url': '/jobticket/api/TEST01/attachments/' + file['id']})
        download = self.request('GET', file['url'])
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, b'PDF\x00\xff original bytes')
        self.assertEqual(download.headers['content-type'], 'application/octet-stream')
        self.assertTrue(download.headers['content-disposition'].startswith('attachment;'))
        self.assertEqual(download.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(download.headers['cache-control'], 'no-store')
        self.assertEqual(self.stored_files(), [file['id']])
        # Upload creates bytes/registry only; attaching them is an explicit ticket PUT.
        self.assertEqual(self.ticket()['state'], self.base)
        with sqlite3.connect(self.app.DB_PATH) as conn:
            row = conn.execute('SELECT job_id,name,size,storage_name FROM attachments').fetchone()
        self.assertEqual(row, ('TEST01', 'cut one.ai', 20, file['id']))

    def test_upload_requires_existing_ticket_without_creating_one(self):
        response = self.upload(job='MISSING01')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.request('GET', '/jobticket/api/MISSING01').status_code, 404)
        self.assertEqual(self.stored_files(), [])

    def test_zero_byte_file_and_unicode_name_download(self):
        response = self.upload(b'', name='café plaque.pdf')
        self.assertEqual(response.status_code, 200, response.text)
        file = response.json()['file']
        self.assertEqual((file['name'], file['size']), ('café plaque.pdf', 0))
        download = self.request('GET', file['url'])
        self.assertEqual(download.content, b'')
        self.assertIn("filename*=utf-8''caf%C3%A9%20plaque.pdf", download.headers['content-disposition'])

    def test_filename_controls_cannot_inject_headers_or_storage_paths(self):
        response = self.upload(name='..\\..\\evil\x00\x7f\r\nname.html')
        self.assertEqual(response.status_code, 200, response.text)
        file = response.json()['file']
        self.assertNotRegex(file['name'], r'[\x00-\x1f\x7f/\\]')
        self.assertEqual(self.stored_files(), [file['id']])
        download = self.request('GET', file['url'])
        self.assertEqual(download.headers['content-type'], 'application/octet-stream')
        self.assertEqual(download.content, b'PDF\x00\xff original bytes')

    def test_exact_100_mib_succeeds_and_one_more_leaves_no_partial_file(self):
        maximum = 104857600
        with tempfile.TemporaryFile() as source:
            for _ in range(100):
                source.write(b'Z' * 1048576)
            source.seek(0)
            response = self.upload(source, name='full-size.bin')
            self.assertEqual(response.status_code, 200, response.text)
            file = response.json()['file']
            self.assertEqual(file['size'], maximum)
            self.assertEqual((self.root / 'attachments' / file['id']).stat().st_size, maximum)
            before = self.stored_files()
            source.seek(0, 2)
            source.write(b'!')
            source.seek(0)
            response = self.upload(source, name='too-large.bin')
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(self.stored_files(), before)
        self.assertEqual(self.ticket()['state'], self.base)
        with sqlite3.connect(self.app.DB_PATH) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM attachments').fetchone()[0], 1)

    def test_registry_failure_removes_only_new_file_and_retains_existing_reference(self):
        state, original = self.attached()
        before = self.ticket()
        files_before = self.stored_files()
        with sqlite3.connect(self.app.DB_PATH) as conn:
            conn.execute("CREATE TRIGGER fail_new_attachment BEFORE INSERT ON attachments BEGIN SELECT RAISE(ABORT, 'Synthetic registry failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.upload(b'failed replacement', 'failed.pdf')
        self.assertEqual(self.ticket(), before)
        self.assertEqual(self.stored_files(), files_before)
        self.assertEqual(self.request('GET', original['url']).content, b'PDF\x00\xff original bytes')
        with sqlite3.connect(self.app.DB_PATH) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM attachments').fetchone()[0], 1)

    def test_unreadable_upload_source_removes_partial_storage(self):
        class UnreadableAfterFirstChunk(io.BytesIO):
            def read(self, size=-1):
                if self.tell():
                    raise OSError('Synthetic input read failure')
                return super().read(size)
        source = UnreadableAfterFirstChunk(b'A' * 1048577)
        file = UploadFile(source, filename='failed.bin')
        with self.assertRaises(OSError):
            asyncio.run(self.app.api_attachment('TEST01', file))
        self.assertTrue(source.closed)
        self.assertEqual(self.stored_files(), [])
        self.assertEqual(self.ticket()['state'], self.base)
        with sqlite3.connect(self.app.DB_PATH) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM attachments').fetchone()[0], 0)

    def test_large_declared_request_rejects_before_receiving_body(self):
        received = []
        async def body():
            received.append(True)
            yield b'--x\r\nContent-Disposition: form-data; name="file"; filename="tiny.ai"\r\n\r\nx\r\n--x--\r\n'
        response = self.request('POST', '/jobticket/api/TEST01/attachments', content=body(),
                                headers={'content-type': 'multipart/form-data; boundary=x',
                                         'content-length': '105906177'})
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(received, [])
        self.assertEqual(self.stored_files(), [])
        with sqlite3.connect(self.app.DB_PATH) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM attachments').fetchone()[0], 0)

    def test_streamed_and_false_length_requests_stop_before_spooling_unbounded_data(self):
        for declared_length in (None, '1'):
            with self.subTest(declared_length=declared_length):
                chunks = []
                async def body():
                    yield b'--x\r\nContent-Disposition: form-data; name="file"; filename="oversize.ai"\r\n\r\n'
                    for index in range(104):
                        chunks.append(index)
                        yield b'X' * 1048576
                    yield b'\r\n--x--\r\n'
                headers = {'content-type': 'multipart/form-data; boundary=x'}
                if declared_length:
                    headers['content-length'] = declared_length
                response = self.request('POST', '/jobticket/api/TEST01/attachments', content=body(), headers=headers)
                self.assertEqual(response.status_code, 413, response.text)
                self.assertLessEqual(len(chunks), 101, 'Body guard must stop receiving at 101 MiB, before the handler')
                self.assertEqual(self.stored_files(), [])
                with sqlite3.connect(self.app.DB_PATH) as conn:
                    self.assertEqual(conn.execute('SELECT COUNT(*) FROM attachments').fetchone()[0], 0)

    def test_attachment_body_guard_does_not_change_image_or_corkboard_routes(self):
        response = self.request('POST', '/jobticket/api/TEST01/image',
                                files={'file': ('tiny.png', b'unchanged image route', 'image/png')},
                                headers={'content-length': '105906177'})
        self.assertEqual(response.status_code, 200, response.text)
        response = self.request('POST', '/jobticket/corkboard/api',
                                json={'operationId': 'unchanged-board-01', 'operations': []},
                                headers={'origin': 'http://localhost:8765', 'content-length': '105906177'})
        self.assertEqual(response.status_code, 200, response.text)

    def test_new_attachment_storage_is_private_under_permissive_umask(self):
        previous_umask = os.umask(0)
        try:
            response = self.upload()
        finally:
            os.umask(previous_umask)
        self.assertEqual(response.status_code, 200, response.text)
        file_id = response.json()['file']['id']
        self.assertIn(stat.S_IMODE((self.root / 'attachments' / file_id).stat().st_mode), (0o600, 0o640))
        self.assertEqual(stat.S_IMODE((self.root / 'attachments').stat().st_mode), 0o750)

    def test_render_preserves_attachment_tokens_and_quoted_job_name(self):
        self.app.TEMPLATE = Path(__file__).resolve().parents[1] / 'frontend' / 'ticket.html'
        file = self.upload(name='__TITLE____BOOTSTRAP__.ai').json()['file']
        name = 'FILES01 1/4" Acrylic </script>'
        state = dict(self.base, jobName=name, materialRowIds=['first', 'second'], materialFiles=[file, None])
        self.assertEqual(self.put(state).status_code, 200)
        response = self.request('GET', '/jobticket/TEST01')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('__TITLE____BOOTSTRAP__.ai' in response.text, 'Bootstrap rewrote attachment filename tokens')
        class Scripts(HTMLParser):
            def __init__(self):
                super().__init__()
                self.scripts = []
                self.active = False
            def handle_starttag(self, tag, attrs):
                if tag == 'script':
                    self.active = not any(key == 'src' for key, value in attrs)
                    if self.active:
                        self.scripts.append('')
            def handle_data(self, data):
                if self.active:
                    self.scripts[-1] += data
            def handle_endtag(self, tag):
                if tag == 'script':
                    self.active = False
        parser = Scripts()
        parser.feed(response.text)
        self.assertEqual(len(parser.scripts), 3)
        boot = json.loads(parser.scripts[0].removeprefix('window.__TICKET__ = ').removesuffix(';'))
        self.assertEqual(boot['state'], state)
        self.assertEqual(boot['jobName'], name)
        self.assertIn('FILES01 1/4&quot; Acrylic &lt;/script&gt; · Job Ticket</title>', response.text)
        self.assertNotIn('</script>', parser.scripts[0])

    def test_download_rejects_other_jobs_unknown_ids_and_paths(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.text)
        file = response.json()['file']
        self.assertEqual(self.put(self.base, job='OTHER01').status_code, 200)
        for path in ('/jobticket/api/OTHER01/attachments/' + file['id'],
                     '/jobticket/api/TEST01/attachments/' + 'a' * 32,
                     '/jobticket/api/TEST01/attachments/not-an-id',
                     '/jobticket/api/TEST01/attachments/%2e%2e%2fapp.py'):
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path).status_code, 404)

    def test_file_metadata_is_canonicalized_from_owning_registry(self):
        state, file = self.attached()
        forged = dict(file, name='<script>evil</script>', size=-1, url='https://evil.example/', extra='ignored')
        self.assertEqual(self.put(dict(state, materialFiles=[forged, None])).status_code, 200)
        self.assertEqual(self.ticket()['state']['materialFiles'], [file, None])

    def test_explicit_fields_reject_invalid_types_lengths_duplicates_and_unowned_files(self):
        state, file = self.attached()
        other = self.upload(job='TEST01').json()['file']
        self.assertEqual(self.put(self.base, 'OTHER01').status_code, 200)
        foreign = self.upload(job='OTHER01').json()['file']
        changes = [
            {'materialRowIds': None}, {'materialFiles': None},
            {'materialRowIds': ['only-one']}, {'materialFiles': [None]},
            {'materialRowIds': ['same', 'same']}, {'materialRowIds': ['', 'valid']},
            {'materialRowIds': [1, 'valid']}, {'materialRowIds': ['a' * 129, 'valid']},
            {'materialFiles': ['not metadata', None]}, {'materialFiles': [{}, None]},
            {'materialFiles': [{'id': '../app.py'}, None]},
            {'materialFiles': [{'id': 'f' * 32}, None]},
            {'materialFiles': [foreign, None]}, {'materials': 'Acrylic'},
        ]
        for change in changes:
            with self.subTest(change=change):
                before = self.ticket()
                response = self.put(dict(state, **change))
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(self.ticket(), before)
        for missing in ('materialFiles', 'materialRowIds'):
            payload = copy.deepcopy(state)
            del payload[missing]
            self.assertEqual(self.put(payload).status_code, 400)
        self.assertEqual(self.request('GET', other['url']).status_code, 200)

    def test_explicit_row_reorder_delete_replace_and_clear_keep_bytes(self):
        state, original = self.attached()
        reordered = dict(state, materialDetails=['Second cut', 'First cut'], materialCompleted=[True, False],
                         materialRowIds=['row-second', 'row-first'], materialFiles=[None, original])
        self.assertEqual(self.put(reordered).status_code, 200)
        self.assertEqual(self.ticket()['state']['materialRowIds'], ['row-second', 'row-first'])
        replacement = self.upload(b'new version', 'replacement.pdf').json()['file']
        remaining = dict(state, materials=['Acrylic'], materialDetails=['First cut'], materialCompleted=[False],
                         materialRowIds=['row-first'], materialFiles=[replacement])
        self.assertEqual(self.put(remaining).status_code, 200)
        self.assertEqual(self.ticket()['state']['materialFiles'], [replacement])
        self.assertEqual(self.put(dict(remaining, materialFiles=[None], materialFileBase={'row-first': replacement['id']})).status_code, 200)
        self.assertEqual(self.ticket()['state']['materialFiles'], [None])
        self.assertEqual(self.request('GET', original['url']).content, b'PDF\x00\xff original bytes')
        self.assertEqual(self.request('GET', replacement['url']).content, b'new version')
        self.assertEqual(len(self.stored_files()), 2)

    def test_stale_explicit_client_cannot_erase_replace_or_delete_another_tab_file(self):
        state, file = self.attached()
        stale = dict(state, materialFiles=[None, None], materialFileBase={'row-first': None, 'row-second': None})
        candidates = [
            stale,
            dict(stale, materialRowIds=['row-second'], materials=['Acrylic'],
                 materialDetails=['Second cut'], materialCompleted=[True], materialFiles=[None]),
            dict(state, materialFileBase={}),
            {key: value for key, value in state.items() if key != 'materialFileBase'},
        ]
        for payload in candidates:
            with self.subTest(payload=payload):
                before = self.ticket()
                response = self.put(payload)
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(self.ticket(), before)
        self.assertEqual(self.put(dict(state, materialFiles=[None, None])).status_code, 200)
        saved = self.ticket()['state']
        self.assertEqual(saved['materialFiles'], [None, None])
        self.assertNotIn('materialFileBase', saved)
        self.assertEqual(self.request('GET', file['url']).status_code, 200)
        # A tab whose saved baseline still had the removed file cannot reattach it.
        self.assertEqual(self.put(state).status_code, 409)

    def test_attachment_base_rejects_invalid_and_nonempty_new_row_expectations(self):
        state = dict(self.base, materialRowIds=['first', 'second'], materialFiles=[None, None])
        for baseline in ([], 'invalid', {'first': 1}, {'first': '../path'}):
            with self.subTest(baseline=baseline):
                response = self.put(dict(state, materialFileBase=baseline))
                self.assertEqual(response.status_code, 400, response.text)
        # A new material row cannot claim a prior saved attachment expectation.
        response = self.put(dict(state, materialFileBase={'first': 'a' * 32}))
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.put(dict(state, materialFileBase={})).status_code, 200)
        self.assertNotIn('materialFileBase', self.ticket()['state'])

    def test_legacy_unrelated_edits_preserve_both_attachment_fields(self):
        state, file = self.attached()
        # Includes a client older than materialDetails/materialCompleted.
        payload = {key: value for key, value in state.items()
                   if key not in ('materialRowIds', 'materialFiles', 'materialDetails', 'materialCompleted')}
        payload['notes'] = 'Old-tab unrelated edit'
        self.assertEqual(self.put(payload).status_code, 200)
        saved = self.ticket()['state']
        self.assertEqual(saved['materialRowIds'], ['row-first', 'row-second'])
        self.assertEqual(saved['materialFiles'], [file, None])
        self.assertEqual(saved['materialDetails'], ['First cut', 'Second cut'])
        self.assertEqual(saved['materialCompleted'], [False, True])
        self.assertEqual(saved['notes'], 'Old-tab unrelated edit')

    def test_legacy_duplicate_row_changes_reject_without_writing(self):
        state, _ = self.attached()
        old = {key: value for key, value in state.items() if key not in ('materialRowIds', 'materialFiles')}
        changes = [
            {'materials': ['Acrylic'], 'materialDetails': ['Second cut'], 'materialCompleted': [True]},
            {'materialDetails': ['Second cut', 'First cut'], 'materialCompleted': [True, False]},
            {'materialDetails': ['Changed first', 'Second cut']}, {'materialCompleted': [True, True]},
            {'materials': ['Renamed', 'Acrylic']},
        ]
        for change in changes:
            with self.subTest(change=change):
                before = self.ticket()
                response = self.put(dict(old, **change, notes='must not persist'))
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(self.ticket(), before)

    def test_legacy_without_attachments_can_change_rows_without_stale_alignment(self):
        state = dict(self.base, materialRowIds=['row-first', 'row-second'], materialFiles=[None, None])
        self.assertEqual(self.put(state).status_code, 200)
        changed = dict(self.base, materials=['Replacement'], materialDetails=['New'], materialCompleted=[False])
        self.assertEqual(self.put(changed).status_code, 200)
        saved = self.ticket()['state']
        self.assertEqual(saved['materials'], ['Replacement'])
        self.assertTrue('materialRowIds' not in saved or len(saved['materialRowIds']) == 1)
        self.assertTrue('materialFiles' not in saved or saved['materialFiles'] == [None])

    def test_attachment_routes_keep_corkboard_functional(self):
        response = self.request('GET', '/jobticket/corkboard/api')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'revision': 0, 'initialized': False, 'pins': []})


if __name__ == '__main__':
    unittest.main()
