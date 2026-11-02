"""Pure sidecar validation; no production access."""
import copy
import importlib.util
from pathlib import Path
import unittest
from fastapi import HTTPException

spec = importlib.util.spec_from_file_location('ticket_rich_text', Path(__file__).resolve().parents[1] / 'backend/rich_text.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
prepare_state = module.prepare_state
EMPTY = {'version': 1, 'fields': {}}

class RichTextTests(unittest.TestCase):
    def state(self):
        return {'jobName': 'Café 🐂', 'notes': 'one\ntwo', 'materials': ['Same', 'Same'], 'materialDetails': ['a', 'b'], 'materialRowIds': ['m1', 'm2'], 'steps': [{'op':'Cut','instr':'Slow'}], 'productionRowIds': ['p1']}
    def rich(self, state, key='jobName', runs=None):
        state['richText'] = {'version':1,'fields': {key: runs if runs is not None else [{'text':state['jobName'],'bold':True}]}}
        return state
    def error(self, state, previous=None, status=400):
        with self.assertRaises(HTTPException) as caught: prepare_state(state, previous)
        self.assertEqual(caught.exception.status_code, status)
    def test_unicode_normalization_and_literal_text(self):
        s=self.rich(self.state(), runs=[{'text':'Café 🐂','bold':False,'italic':True,'underline':True,'size':48,'color':'#Ab12Ef','highlight':'#FEF08A'}]); prepare_state(s,None)
        self.assertEqual(s['richText']['fields']['jobName'][0]['color'],'#ab12ef')
        self.assertIs(s['richText']['fields']['jobName'][0]['bold'],False)
    def test_invalid_runs(self):
        for run in ({'text':'wrong'}, {'text':'Café 🐂','html':'<script>'}, {'text':'Café 🐂','color':'url(x)'}, {'text':'Café 🐂','size':True}, {'text':'Café 🐂','size':49}, {'text':'Café 🐂','bold':1}, {'text':'Café 🐂','highlight':'#ffffff'}):
            with self.subTest(run=run): self.error(self.rich(self.state(),runs=[run]))
    def test_invalid_field_and_schema(self):
        for key in ('__proto__','jobNumber','material:missing:name','production:p1:html'):
            self.error(self.rich(self.state(),key,[{'text':'x'}]))
    def test_clear_and_baseline(self):
        old=self.rich(self.state()); s=self.state(); s['richText']=copy.deepcopy(EMPTY)
        self.error(copy.deepcopy(s),old,409)
        s['richTextBase']=old['richText']; prepare_state(s,old)
        self.assertEqual(s['richText'],EMPTY); self.assertNotIn('richTextBase',s)
    def test_old_tab_preserves_and_rejects_changed_text(self):
        old=self.rich(self.state()); s=self.state(); prepare_state(s,old); self.assertEqual(s['richText'],old['richText'])
        s=self.state(); s['jobName']='new'; self.error(s,old,409)
    def test_production_ids_omission(self):
        old=self.rich(self.state(),'production:p1:op',[{'text':'Cut','italic':True}]); s=self.state(); del s['productionRowIds']; prepare_state(s,old); self.assertEqual(s['productionRowIds'],['p1'])
        s=self.state(); del s['productionRowIds']; s['steps']=[]; self.error(s,old,409)
    def test_ids_invalid(self):
        for ids in (['p1','p1'],['bad:id'],[3],[]):
            s=self.state(); s['productionRowIds']=ids; self.error(s)
    def test_quantities_validation(self):
        for qty in (['0','123456789'],['','12']):
            s=self.state(); s['materialQuantities']=qty; prepare_state(s,None); self.assertEqual(s['materialQuantities'],qty)
        for qty in (['1'],['-1',''],['1.5',''],[1,''],['1234567890',''],[' 1','']):
            s=self.state(); s['materialQuantities']=qty; self.error(s)
    def test_duplicate_delete_preserves_by_id(self):
        old=self.rich(self.state(),'material:m2:name',[{'text':'Same','underline':True}]); old['materialQuantities']=['2','17']; s=self.state(); s.update(materials=['Same'],materialDetails=['b'],materialRowIds=['m2']); prepare_state(s,old)
        self.assertEqual(s['materialQuantities'],['17']); self.assertEqual(s['richText'],old['richText'])
    def test_ambiguous_old_quantity_change_rejected(self):
        old=self.state(); old['materialQuantities']=['2','17']; s=self.state(); del s['materialRowIds']; s['materials']=['Same']; self.error(s,old,409)
        s=self.state(); del s['materialRowIds']; prepare_state(s,old); self.assertEqual(s['materialQuantities'],['2','17'])

    def test_preserve_plain_fields_and_previous_unchanged(self):
        old=self.rich(self.state()); original=copy.deepcopy(old); s=self.state(); s['custom']={'preserve':True}; prepare_state(s,old)
        self.assertEqual(old,original); self.assertEqual(s['custom'],{'preserve':True})
    def test_explicit_false_marks_and_empty_text(self):
        s=self.rich(self.state(),'notes',[{'text':'one\ntwo','bold':False,'italic':False,'underline':False}]); prepare_state(s,None)
        self.assertIs(s['richText']['fields']['notes'][0]['bold'],False)
        s=self.rich(self.state(),'notes',[]); s['notes']=''; prepare_state(s,None); self.assertEqual(s['richText']['fields']['notes'],[])
    def test_bounds(self):
        self.error(self.rich(self.state(),runs=[{'text':''}]*10001))
        self.error(self.rich(self.state(),runs=[{'text':'x'*1000001}]))
        s=self.state(); s['steps']=[{}]*2001; self.error(s)
    def test_stale_baseline_even_when_sidecar_omitted(self):
        old=self.rich(self.state()); s=self.state(); s['richTextBase']=EMPTY; self.error(s,old,409)
    def test_material_formatting_without_ids_rejects_duplicate_deletion(self):
        old=self.rich(self.state(),'material:m2:name',[{'text':'Same','bold':True}]); s=self.state(); del s['materialRowIds']; s['materials']=['Same']; s['materialDetails']=['b']; self.error(s,old,409)
    def test_reordered_ids_keep_quantities(self):
        old=self.state(); old['materialQuantities']=['7','21']; s=self.state(); s['materialRowIds']=['m2','m1']; s['materialDetails']=['b','a']; prepare_state(s,old); self.assertEqual(s['materialQuantities'],['21','7'])

if __name__=='__main__': unittest.main()

class RichTextApiShapeTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from test_backend import load_isolated_backend
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        import sqlite3
        from unittest.mock import patch
        connections=[]
        original_connect=sqlite3.connect
        def connect(*args, **kwargs):
            kwargs['check_same_thread']=False
            conn=original_connect(*args, **kwargs); connections.append(conn); return conn
        connection_patch=patch.object(sqlite3,'connect',connect)
        connection_patch.start()
        self.addCleanup(connection_patch.stop)
        self.addCleanup(lambda: [conn.close() for conn in connections])
        self.app = load_isolated_backend(Path(self.directory.name))
        self.base = {'jobName':'SHAPE01 test','notes':'','materials':['Same'],
                     'materialDetails':['detail'],'materialRowIds':['m1'],'materialFiles':[None],
                     'steps':[], 'productionRowIds':[], 'richText':copy.deepcopy(EMPTY)}
        self.assertEqual(self.request('PUT',self.base).status_code,200)
    def request(self, method, state=None):
        import asyncio
        import httpx
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app.app,raise_app_exceptions=False),base_url='http://testserver') as client:
                return await client.request(method,'/jobticket/api/SHAPE01',**({'json':state} if state is not None else {}))
        return asyncio.run(send())
    def test_malformed_material_details_rejected_without_write(self):
        before=self.request('GET').json()
        for value in (None,17,{'0':'detail'}):
            with self.subTest(value=value):
                state=copy.deepcopy(self.base); state['materialDetails']=value
                self.assertEqual(self.request('PUT',state).status_code,400)
                self.assertEqual(self.request('GET').json(),before)
    def test_unformatted_legacy_malformed_details_can_be_repaired(self):
        import json
        for value in (None,17,{'0':'detail'}):
            with self.subTest(value=value):
                legacy=copy.deepcopy(self.base); legacy.pop('richText'); legacy['materialDetails']=value
                with self.app.db() as conn:
                    conn.execute('UPDATE tickets SET data=? WHERE job_id=?',(json.dumps(legacy),'SHAPE01'))
                self.assertEqual(self.request('PUT',copy.deepcopy(self.base)).status_code,200)
                self.assertEqual(self.request('GET').json()['state']['materialDetails'],['detail'])
    def test_legacy_bad_details_with_unrelated_formatting_can_be_repaired(self):
        import json
        legacy=copy.deepcopy(self.base)
        legacy['richText']['fields']['jobName']=[{'text':legacy['jobName'],'bold':True}]
        legacy['materialDetails']=None
        with self.app.db() as conn:
            conn.execute('UPDATE tickets SET data=? WHERE job_id=?',(json.dumps(legacy),'SHAPE01'))
        state=copy.deepcopy(self.base); state.pop('richText')
        self.assertEqual(self.request('PUT',state).status_code,200)
        self.assertEqual(self.request('GET').json()['state']['richText'],legacy['richText'])
    def test_legacy_bad_formatted_details_rejects_without_guessing(self):
        import json
        legacy=copy.deepcopy(self.base)
        legacy['richText']['fields']['material:m1:details']=[{'text':'detail','bold':True}]
        legacy['materialDetails']=None
        with self.app.db() as conn:
            conn.execute('UPDATE tickets SET data=? WHERE job_id=?',(json.dumps(legacy),'SHAPE01'))
        before=self.request('GET').json()
        state=copy.deepcopy(self.base); state.pop('richText')
        self.assertEqual(self.request('PUT',state).status_code,400)
        self.assertEqual(self.request('GET').json(),before)
