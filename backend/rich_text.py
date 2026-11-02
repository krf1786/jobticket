"""Bounded literal rich-text sidecars and conservative legacy-save compatibility."""
import copy
import re
from fastapi import HTTPException

ID = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
HEX = re.compile(r'#[0-9a-fA-F]{6}\Z')
QTY = re.compile(r'[0-9]{1,9}\Z')
EMPTY = {'version': 1, 'fields': {}}
MAX_ROWS = 2000
MAX_TEXT = 1_000_000
MAX_RUNS = 10000


def invalid(message='Invalid ticket text formatting.'):
    raise HTTPException(400, message)


def conflict():
    raise HTTPException(409, 'Ticket formatting or quantities changed. Reload the updated editor before saving.')


def ids_for(state, key, rows):
    if key not in state:
        return None
    values = state[key]
    if (not isinstance(values, list) or len(values) != len(rows)
            or any(not isinstance(v, str) or not ID.fullmatch(v) for v in values)
            or len(set(values)) != len(values)):
        invalid('Row IDs must be unique safe identifiers aligned with their rows.')
    return values


def row_data(state, field):
    rows = state.get(field, [])
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        invalid('Invalid ticket rows.')
    return rows


def fields_for(state):
    fields = {k: state.get(k, '') for k in ('jobName', 'notes')}
    for row_id, index in zip(state.get('materialRowIds', []), range(len(state.get('materials', [])))):
        fields[f'material:{row_id}:name'] = state['materials'][index]
        details = state.get('materialDetails', [])
        fields[f'material:{row_id}:details'] = details[index] if index < len(details) else ''
    for row_id, row in zip(state.get('productionRowIds', []), state.get('steps', [])):
        if not isinstance(row, dict):
            invalid('Invalid production row.')
        for key in ('op', 'instr'):
            fields[f'production:{row_id}:{key}'] = row.get(key, '')
    return fields


def normalize(value, fields=None):
    if (not isinstance(value, dict) or set(value) != {'version', 'fields'}
            or type(value['version']) is not int or value['version'] != 1
            or not isinstance(value['fields'], dict) or len(value['fields']) > MAX_ROWS * 4 + 2):
        invalid()
    result = {'version': 1, 'fields': {}}
    total_runs = total_text = 0
    for key, runs in value['fields'].items():
        if (not isinstance(key, str) or not (key in ('jobName', 'notes') or
                re.fullmatch(r'(material:[A-Za-z0-9_-]{1,128}:(name|details)|production:[A-Za-z0-9_-]{1,128}:(op|instr))', key))
                or (fields is not None and key not in fields) or not isinstance(runs, list)):
            invalid()
        clean = []
        for run in runs:
            total_runs += 1
            if total_runs > MAX_RUNS or not isinstance(run, dict) or 'text' not in run or set(run) - {'text','bold','italic','underline','size','color','highlight'}:
                invalid()
            if not isinstance(run['text'], str):
                invalid()
            total_text += len(run['text'])
            if total_text > MAX_TEXT:
                invalid()
            item = dict(run)
            for mark in ('bold', 'italic', 'underline'):
                if mark in item and type(item[mark]) is not bool:
                    invalid()
            if 'size' in item and (type(item['size']) is not int or not 8 <= item['size'] <= 48):
                invalid()
            for mark in ('color', 'highlight'):
                if mark in item:
                    if not isinstance(item[mark], str) or not HEX.fullmatch(item[mark]):
                        invalid()
                    item[mark] = item[mark].lower()
            if 'highlight' in item and item['highlight'] not in ('#fef08a', '#fbcfe8', '#bbf7d0'):
                invalid()
            clean.append(item)
        if fields is not None and ''.join(r['text'] for r in clean) != fields[key]:
            invalid('Formatted text must exactly match its plain field.')
        result['fields'][key] = clean
    return result


def unchanged_materials(state, previous):
    return all(state.get(k) == previous.get(k) for k in ('materials', 'materialDetails', 'materialCompleted'))


def prepare_state(state: dict, previous: dict | None) -> None:
    """Validate in memory before writing; never modify the previous ticket."""
    previous = previous or {}
    materials = row_data(state, 'materials')
    steps = row_data(state, 'steps')
    material_ids = ids_for(state, 'materialRowIds', materials)
    production_ids = ids_for(state, 'productionRowIds', steps)
    old_rich = normalize(previous.get('richText', EMPTY))
    old_fields = fields_for(previous)
    if production_ids is None and 'productionRowIds' in previous and steps == previous.get('steps', []):
        state['productionRowIds'] = copy.deepcopy(previous['productionRowIds'])
    if material_ids is None and 'materialRowIds' in previous and unchanged_materials(state, previous):
        state['materialRowIds'] = copy.deepcopy(previous['materialRowIds'])
    fields = fields_for(state)
    base_supplied = 'richTextBase' in state
    baseline = state.pop('richTextBase', EMPTY)
    if ('richText' in state or base_supplied) and normalize(baseline) != old_rich:
        conflict()
    if 'richText' in state:
        state['richText'] = normalize(state['richText'], fields)
    else:
        # Omitted sidecars are old clients. Exact IDs permit intentional row
        # deletion, while missing IDs cannot establish which duplicate survived.
        preserved = {}
        for key, runs in old_rich['fields'].items():
            if key in fields:
                if fields[key] != old_fields.get(key):
                    conflict()
                preserved[key] = copy.deepcopy(runs)
            elif key.startswith('material:') and material_ids is not None:
                continue
            elif key.startswith('production:') and production_ids is not None:
                continue
            else:
                conflict()
        if 'richText' in previous:
            state['richText'] = {'version': 1, 'fields': preserved}
    if 'materialQuantities' in state:
        quantities = state['materialQuantities']
        if (not isinstance(quantities, list) or len(quantities) != len(materials)
                or any(not isinstance(q, str) or (q != '' and not QTY.fullmatch(q)) for q in quantities)):
            invalid('Material quantities must be blank or nonnegative integers of up to nine digits.')
    elif 'materialQuantities' in previous:
        quantities = previous['materialQuantities']
        old_ids = previous.get('materialRowIds')
        if material_ids is not None and isinstance(old_ids, list) and len(old_ids) == len(quantities):
            by_id = dict(zip(old_ids, quantities))
            state['materialQuantities'] = [by_id.get(i, '') for i in material_ids]
        elif unchanged_materials(state, previous):
            state['materialQuantities'] = copy.deepcopy(quantities)
        elif any(q != '' for q in quantities):
            conflict()
        else:
            state['materialQuantities'] = [''] * len(materials)
