"""Real handlers and SQLite; only PDF/Graph transport is replaced for race control.

Run with: python -m unittest discover -s tests -v
JOBTICKET_BACKEND_SOURCE may select the immutable deployed baseline for red runs.
No production service, credentials, database or Graph endpoint is accessed.
"""
import asyncio
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SOURCE = Path(os.environ.get('JOBTICKET_BACKEND_SOURCE', Path(__file__).resolve().parents[1] / 'backend')).resolve()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Request:
    def __init__(self, data):
        self.data = copy.deepcopy(data)

    async def json(self):
        return self.data


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        # The captured db() context relies on GC to close connections. Keep
        # fixture-owned handles alive and close them explicitly at teardown,
        # including handles created by the controlled push threads.
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
        for name in ('app.py', 'graph.py', 'pdf.py'):
            shutil.copyfile(SOURCE / name, root / name)
        graph = load('isolated_graph', root / 'graph.py')
        pdf = load('isolated_pdf', root / 'pdf.py')
        # Suppress only import-time background work in this synthetic database.
        with patch.dict(sys.modules, {'graph': graph, 'pdf': pdf}), patch.object(threading.Thread, 'start'):
            self.app = load('isolated_app', root / 'app.py')
        self.app.graph.enabled = lambda: True
        self.app.graph.status = lambda: {'enabled': True, 'missing': []}
        self.app.pdf.available = lambda: True
        self.base = {'jobName': 'TEST01 synthetic', 'materials': ['Clear acrylic', 'White acrylic'],
                     'materialDetails': ['Polish edges', 'Matte finish'], 'notes': '', 'image': None}
        self.put(self.base)

    def put(self, state, job='TEST01'):
        return asyncio.run(self.app.api_put(job, Request(state)))

    def state(self):
        return self.app.api_get('TEST01')['state']

    def legacy(self, **changes):
        data = {k: v for k, v in self.base.items() if k != 'materialDetails'}
        data.update(changes)
        return data

    def thread(self, action):
        results, errors = [], []
        def run():
            try:
                results.append(action())
            except Exception as error:
                errors.append(error)
        worker = threading.Thread(target=run)
        worker.start()
        return worker, results, errors

    def finish(self, task):
        worker, results, errors = task
        worker.join(5)
        self.assertFalse(worker.is_alive(), 'Push thread did not finish')
        self.assertFalse(errors, errors)
        self.assertTrue(results[0]['ok'], results)

    def test_legacy_unrelated_edits_preserve_details(self):
        self.put(self.legacy(notes='Changed by an old tab'))
        self.assertEqual(self.state().get('materialDetails'), self.base['materialDetails'])
        self.assertEqual(self.state()['notes'], 'Changed by an old tab')
        self.put(self.legacy(notes='A second old-tab edit'))
        self.assertEqual(self.state().get('materialDetails'), self.base['materialDetails'])

    def test_legacy_material_changes_with_details_reject_without_writing(self):
        for materials in (['White acrylic'], ['White acrylic', 'Clear acrylic'], ['Renamed acrylic', 'White acrylic'], ['']):
            with self.subTest(materials=materials):
                before = self.app.api_get('TEST01')
                with self.assertRaises(self.app.HTTPException) as error:
                    self.put(self.legacy(materials=materials, jobName='Must not persist'))
                self.assertEqual(error.exception.status_code, 409)
                self.assertEqual(self.app.api_get('TEST01'), before)

    def test_duplicate_materials_are_not_guessed_by_legacy_deletion(self):
        duplicate = dict(self.base, materials=['Acrylic', 'Acrylic'], materialDetails=['First cut', 'Second cut'])
        self.put(duplicate)
        with self.assertRaises(self.app.HTTPException) as error:
            self.put({'jobName': duplicate['jobName'], 'materials': ['Acrylic']})
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.state(), duplicate)

    def test_updated_client_can_clear_details_explicitly(self):
        for details in (['', ''], []):
            with self.subTest(details=details):
                self.put(dict(self.base, materialDetails=details))
                self.assertEqual(self.state()['materialDetails'], details)

    def test_updated_client_deletion_keeps_the_surviving_detail(self):
        self.put(dict(self.base, materials=['White acrylic'], materialDetails=['Matte finish']))
        self.assertEqual(self.state()['materials'], ['White acrylic'])
        self.assertEqual(self.state()['materialDetails'], ['Matte finish'])

    def test_updated_client_reset_clears_materials_and_details(self):
        self.put({'jobName': '', 'materials': [''], 'materialDetails': [''], 'notes': '', 'image': None})
        self.assertEqual(self.state()['materials'], [''])
        self.assertEqual(self.state().get('materialDetails'), [''])

    def test_old_tickets_without_details_keep_legacy_behavior(self):
        self.put(self.legacy(), 'OLD01')
        self.put(self.legacy(materials=['Replacement material']), 'OLD01')
        saved = self.app.api_get('OLD01')['state']
        self.assertEqual(saved['materials'], ['Replacement material'])
        self.assertNotIn('materialDetails', saved)

    def test_legacy_rows_with_only_blank_details_can_change(self):
        self.put(dict(self.base, materialDetails=['', '']))
        self.put(self.legacy(materials=['Replacement material']))
        self.assertEqual(self.state()['materials'], ['Replacement material'])
        self.assertEqual(self.state().get('materialDetails'), [''])

    def test_legacy_preserves_completion_and_details_independently(self):
        self.put(dict(self.base, materialCompleted=[True, False]))
        self.put(self.legacy(notes='Old tab edit'))
        self.assertEqual(self.state().get('materialCompleted'), [True, False])
        self.assertEqual(self.state()['materialDetails'], self.base['materialDetails'])
        self.put(dict(self.base, materialDetails=['Updated details', '']))
        self.assertEqual(self.state().get('materialCompleted'), [True, False])
        self.assertEqual(self.state()['materialDetails'][0], 'Updated details')

    def test_legacy_row_changes_with_completion_reject_without_writing(self):
        self.put(dict(self.base, materialDetails=['', ''], materialCompleted=[True, False]))
        before = self.app.api_get('TEST01')
        for payload in (self.legacy(materials=['Changed']), dict(self.base, materials=['Changed'], materialDetails=[''])):
            with self.subTest(payload=payload):
                with self.assertRaises(self.app.HTTPException) as error:
                    self.put(payload)
                self.assertEqual(error.exception.status_code, 409)
                self.assertEqual(self.app.api_get('TEST01'), before)

    def test_explicit_completion_uncheck_delete_and_reset(self):
        self.put(dict(self.base, materialCompleted=[True, True]))
        for materials, details, completed in [(['Clear acrylic', 'White acrylic'], ['Polish edges', 'Matte finish'], [False, True]), (['White acrylic'], ['Matte finish'], [True]), ([''], [''], [False])]:
            self.put(dict(self.base, materials=materials, materialDetails=details, materialCompleted=completed))
            self.assertEqual(self.state()['materialCompleted'], completed)
            self.assertEqual(self.state()['materials'], materials)

    def test_legacy_rows_with_unchecked_completion_can_change(self):
        self.put(dict(self.base, materialDetails=['', ''], materialCompleted=[False, False]))
        self.put(self.legacy(materials=['Replacement']))
        self.assertEqual(self.state().get('materialCompleted'), [False])
        self.assertEqual(self.state()['materialDetails'], [''])

    def test_save_during_pdf_render_remains_stale(self):
        entered, release = threading.Event(), threading.Event()
        captured = []
        def render(url):
            captured.append(self.state())
            entered.set()
            if not release.wait(5): raise RuntimeError('Render gate timed out')
            return b'older PDF'
        self.app.pdf.render = render
        self.app.graph.upload = lambda *args: {'name': 'synthetic.pdf'}
        before = self.app.api_get('TEST01')['updatedAt']
        task = self.thread(lambda: self.app.push_ticket('TEST01'))
        try:
            self.assertTrue(entered.wait(5))
            self.put(dict(self.base, materialDetails=['Newer than PDF', 'Matte finish']))
        finally:
            release.set()
            self.finish(task)
        self.assertEqual(captured[0]['materialDetails'], self.base['materialDetails'])
        self.assertTrue(self.app.api_sync_status('TEST01')['stale'])
        self.assertEqual(self.app.api_sync_status('TEST01')['pushedAt'], before)

    def test_save_during_upload_remains_stale_until_next_push(self):
        entered, release = threading.Event(), threading.Event()
        blobs = []
        self.app.pdf.render = lambda url: json.dumps(self.state()).encode()
        def upload(folder, name, blob):
            blobs.append(blob)
            if len(blobs) == 1:
                entered.set()
                if not release.wait(5): raise RuntimeError('Upload gate timed out')
            return {'name': name}
        self.app.graph.upload = upload
        task = self.thread(lambda: self.app.push_ticket('TEST01'))
        try:
            self.assertTrue(entered.wait(5))
            self.put(dict(self.base, materialDetails=['Newer than upload', 'Matte finish']))
        finally:
            release.set()
            self.finish(task)
        self.assertTrue(self.app.api_sync_status('TEST01')['stale'])
        self.assertTrue(self.app.push_ticket('TEST01')['ok'])
        self.assertFalse(self.app.api_sync_status('TEST01')['stale'])
        self.assertEqual(json.loads(blobs[-1])['materialDetails'][0], 'Newer than upload')

    def test_overlapping_pushes_cannot_finish_with_an_older_pdf(self):
        first_upload, release_first, second_uploaded = threading.Event(), threading.Event(), threading.Event()
        completed = []
        self.app.pdf.render = lambda url: json.dumps(self.state()).encode()
        def upload(folder, name, blob):
            value = json.loads(blob)['materialDetails'][0]
            if value == 'Polish edges':
                first_upload.set()
                if not release_first.wait(5): raise RuntimeError('Upload gate timed out')
            else:
                second_uploaded.set()
            completed.append(value)
            return {'name': name}
        self.app.graph.upload = upload
        first = self.thread(lambda: self.app.push_ticket('TEST01'))
        second = None
        try:
            self.assertTrue(first_upload.wait(5))
            self.put(dict(self.base, materialDetails=['Newest PDF', 'Matte finish']))
            second = self.thread(lambda: self.app.push_ticket('TEST01'))
            # Baseline lets this finish first; repaired code queues behind the held push.
            second_uploaded.wait(.25)
        finally:
            release_first.set()
            self.finish(first)
            if second: self.finish(second)
        self.assertEqual(completed, ['Polish edges', 'Newest PDF'])
        self.assertFalse(self.app.api_sync_status('TEST01')['stale'])

    def test_failed_upload_does_not_acknowledge_and_can_retry(self):
        self.app.pdf.render = lambda url: b'PDF'
        self.app.graph.upload = lambda *args: (_ for _ in ()).throw(RuntimeError('Synthetic failure'))
        self.assertFalse(self.app.push_ticket('TEST01')['ok'])
        self.assertEqual(self.app.api_sync_status('TEST01')['pushedAt'], 0)
        self.assertTrue(self.app.api_sync_status('TEST01')['stale'])
        self.app.graph.upload = lambda *args: {'name': 'synthetic.pdf'}
        self.assertTrue(self.app.push_ticket('TEST01')['ok'])
        self.assertFalse(self.app.api_sync_status('TEST01')['stale'])

    def test_save_revision_increases_even_when_wall_clock_does_not(self):
        before = self.app.api_get('TEST01')['updatedAt']
        with patch.object(self.app.time, 'time', return_value=before):
            self.put(dict(self.base, notes='Same clock tick'))
        after = self.app.api_get('TEST01')['updatedAt']
        self.assertGreater(after, before)
        with patch.object(self.app.time, 'time', return_value=before - 60):
            self.put(dict(self.base, notes='Clock moved backwards'))
        self.assertGreater(self.app.api_get('TEST01')['updatedAt'], after)


if __name__ == '__main__':
    unittest.main()
