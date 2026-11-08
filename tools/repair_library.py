"""Rebuild/check the single-file library, using only Python's standard library.

Usage: python tools/repair_library.py [--check]
Definitions missing from the bin archive are recovered from the author's sketch.
Only 74HC00/04/20/86 receive datasheet-based pin/metadata corrections.
"""
from pathlib import Path
import argparse
import json
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / '74HCxx Series.fzbz'
PINS = {
    '74HC00': '1A 1B 1Y 2A 2B 2Y GND 3Y 3A 3B 4Y 4A 4B VCC'.split(),
    '74HC04': '1A 1Y 2A 2Y 3A 3Y GND 4Y 4A 5Y 5A 6Y 6A VCC'.split(),
    '74HC20': '1A 1B NC 1C 1D 1Y GND 2Y 2A 2B NC 2C 2D VCC'.split(),
    '74HC86': '1A 1B 1Y 2A 2B 2Y GND 3Y 3A 3B 4Y 4A 4B VCC'.split(),
}


def read_zip(path):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(set(archive.namelist()))
        return {name: archive.read(name) for name in archive.namelist()}


def xml_bytes(element):
    return ET.tostring(element, encoding='utf-8', xml_declaration=True)


def asset_name(view):
    return 'svg.' + view.find('layers').get('image').replace('/', '.')


def normalized(name):
    return 'NC' if name.lower() == 'n.c.' else name.upper()


def check(files):
    bin_name = next(n for n in files if n.endswith('.fzb'))
    instances = ET.fromstring(files[bin_name]).findall('instances/instance')
    module_ids = [i.get('moduleIdRef') for i in instances]
    assert len(module_ids) == len(set(module_ids)), 'duplicate bin entry'
    checked = set()
    for module_id in module_ids:
        part = ET.fromstring(files['part.' + module_id + '.fzp'])
        assert part.get('moduleId') == module_id
        chip = re.match(r'74HC\d+', module_id)[0]
        connectors = part.findall('connectors/connector')
        if chip in PINS:
            assert len(connectors) == 14
            assert [c.get('id') for c in connectors] == [f'connector{i}' for i in range(14)]
            assert [normalized(c.get('name')) for c in connectors] == PINS[chip]
            checked.add(chip)
        for view in part.find('views'):
            svg = ET.fromstring(files[asset_name(view)])
            ids = [e.get('id') for e in svg.iter() if e.get('id')]
            assert len(ids) == len(set(ids)), (chip, view.tag, 'duplicate SVG ID')
            by_id = {e.get('id'): e for e in svg.iter() if e.get('id')}
            for layer in view.findall('layers/layer'):
                assert layer.get('layerId') in by_id, (chip, view.tag, 'missing layer')
            for connector in connectors:
                for mapping in connector.findall('views/' + view.tag + '/p'):
                    assert mapping.get('svgId') in by_id
                    if mapping.get('terminalId'):
                        assert mapping.get('terminalId') in by_id
            if chip in PINS and view.tag in ('breadboardView', 'schematicView'):
                assert not any(e.get('transform') for e in svg.iter())
                for i, expected in enumerate(PINS[chip]):
                    term = by_id[f'connector{i}terminal']
                    x = float(term.get('x', 0)) + float(term.get('width', 0))/2
                    y = float(term.get('y', 0)) + float(term.get('height', 0))/2
                    if view.tag == 'breadboardView':
                        assert abs(x - (50 + 100*(i if i < 7 else 13-i))) < .01
                        assert abs(y - (315 if i < 7 else 15)) < .01
                    else:
                        width = float(svg.get('viewBox').split()[2])
                        assert abs(x - (.05 if i < 7 else width+.05)) < .01
                        assert abs(y - 100*(i+1 if i < 7 else 14-i)) < .01
                        label = by_id[f'label{i}']
                        assert normalized(''.join(label.itertext()).strip()) == expected
                        assert float(label.get('font-size', '41.6667')) < 60
    assert checked == set(PINS)
    return {'unique_parts': len(module_ids), 'datasheet_checked_parts': sorted(checked),
            'datasheet_checked_pins': 56, 'all_bin_definitions_and_view_references': 'passed',
            'fritzing_gui_import': 'not tested'}


def rebuild():
    files = read_zip(LIBRARY)
    sketch = read_zip(ROOT / 'images/all_chips.fzz')
    bin_name = next(n for n in files if n.endswith('.fzb'))
    bin_root = ET.fromstring(files[bin_name])
    bin_root.attrib.pop('icon', None)  # The referenced Custom1.png is not bundled.
    instances = bin_root.find('instances')
    seen, restored = set(), []
    for instance in list(instances):
        module_id = instance.get('moduleIdRef')
        if module_id in seen:
            instances.remove(instance)
            continue
        seen.add(module_id)
        instance.set('path', module_id + '.fzp')
        name = 'part.' + module_id + '.fzp'
        if name not in files:
            files[name] = sketch[name]
            restored.append(module_id)
        before = files[name]
        part = ET.fromstring(before)
        chip = re.match(r'74HC\d+', module_id)[0]
        if chip in PINS:
            props = {e.get('name'): e for e in part.findall('properties/property')}
            props['variant'].text = chip
            for i, connector in enumerate(part.findall('connectors/connector')):
                connector.set('name', PINS[chip][i])
            if chip == '74HC04':
                part.find("connectors/connector[@id='connector5']/description").text = 'data output'
        for view in part.find('views'):
            ref = asset_name(view)
            if ref not in files:
                kind = view.tag[:-4]
                candidates = [n for n in files if n.startswith('svg.' + kind + '.' + chip + '_')
                              or n.startswith('svg.' + kind + '.' + chip + ' -')]
                assert len(candidates) == 1, (chip, kind, candidates)
                ref = candidates[0]
                view.find('layers').set('image', kind + '/' + ref[len('svg.' + kind + '.'):])
            # Mechanical icon-layer correction for every bundled part.
            if view.tag == 'iconView':
                files[ref] = files[ref].replace(b'id="breadboard"', b'id="icon"')
            if chip in PINS and view.tag == 'schematicView':
                data = files[ref].replace(b'pin61Y', b'1Y').replace(b'font-size="540.123"', b'font-size="41.6667"')
                data = data.replace(b'Vcc', b'VCC').replace(b'n.c.', b'NC')
                data = re.sub(rb'(<text\b[^>]*\bid="label"[^>]*>)IC(</text>)',
                              lambda m: m[1] + chip.encode() + m[2], data)
                files[ref] = data
        if ET.tostring(ET.fromstring(before)) != ET.tostring(part):
            version = part.find('version')
            version.text = str(int(version.text) + 1)
        files[name] = xml_bytes(part)
    files[bin_name] = xml_bytes(bin_root)
    result = check(files)
    # Fixed member timestamps/order make subsequent rebuilds byte-reproducible.
    temp = LIBRARY.with_suffix('.tmp')
    with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name])
    temp.replace(LIBRARY)
    result['restored_definitions'] = restored
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate without changing the archive')
    args = parser.parse_args()
    print(json.dumps(check(read_zip(LIBRARY)) if args.check else rebuild(), indent=2))
