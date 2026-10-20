import os
import tarfile
import tempfile
import shutil
from lxml import etree
import json

def check_no_bom(filepath):
    with open(filepath, 'rb') as f:
        start = f.read(4)
        if start.startswith(b'\xef\xbb\xbf'):
            return False
    return True

def check_utf8(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            f.read()
        return True
    except Exception:
        return False

def check_json(s):
    try:
        json.loads(s)
        return True
    except Exception:
        return False

def check_library_tar(tar_path):
    tmp = tempfile.mkdtemp()
    try:
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(tmp)
        # 1. Kiểm tra thư mục library/
        lib_dir = os.path.join(tmp, 'library')
        if not os.path.isdir(lib_dir):
            print('❌ Không có thư mục library/ ở gốc!')
            return
        # 2. Kiểm tra file library.xml, policies/assets.json, problem/
        libxml = os.path.join(lib_dir, 'library.xml')
        assets = os.path.join(lib_dir, 'policies', 'assets.json')
        prob_dir = os.path.join(lib_dir, 'problem')
        if not os.path.isfile(libxml):
            print('❌ Thiếu library.xml trong library/')
        if not os.path.isfile(assets):
            print('❌ Thiếu policies/assets.json trong library/')
        if not os.path.isdir(prob_dir):
            print('❌ Thiếu thư mục problem/ trong library/')
        # 3. Kiểm tra assets.json
        with open(assets, encoding='utf-8') as f:
            content = f.read().strip()
            if content != '{}':
                print(f'❌ policies/assets.json phải là {{}} nhưng là: {content}')
        # 4. Kiểm tra library.xml
        if not check_no_bom(libxml):
            print('❌ library.xml có BOM!')
        if not check_utf8(libxml):
            print('❌ library.xml không phải utf-8!')
        with open(libxml, encoding='utf-8') as f:
            xml = f.read()
        try:
            root = etree.fromstring(xml.encode('utf-8'))
        except Exception as e:
            print(f'❌ library.xml lỗi parse XML: {e}')
            return
        # Kiểm tra namespace, thứ tự thẻ con, tags
        tags_attr = root.attrib.get('tags', '')
        if not check_json(tags_attr):
            print(f'❌ library.xml: tags không phải mảng JSON: {tags_attr}')
        # 5. Kiểm tra từng problem XML
        for fname in os.listdir(prob_dir):
            if not fname.endswith('.xml'): continue
            fpath = os.path.join(prob_dir, fname)
            if not check_no_bom(fpath):
                print(f'❌ {fname} có BOM!')
            if not check_utf8(fpath):
                print(f'❌ {fname} không phải utf-8!')
            with open(fpath, encoding='utf-8') as f:
                xml = f.read()
            try:
                root = etree.fromstring(xml.encode('utf-8'))
            except Exception as e:
                print(f'❌ {fname} lỗi parse XML: {e}')
                continue
            # Kiểm tra tags
            tags_attr = root.attrib.get('tags', '')
            if not check_json(tags_attr):
                print(f'❌ {fname}: tags không phải mảng JSON: {tags_attr}')
            # Kiểm tra <choice> không rỗng
            for cg in root.findall('.//choicegroup'):
                for c in cg.findall('choice'):
                    if not (c.text and c.text.strip()):
                        print(f'❌ {fname}: <choice> rỗng!')
            # Kiểm tra thẻ lạ
            for elem in root.iter():
                if elem.tag not in ['problem','multiplechoiceresponse','choicegroup','choice','p','h3','label','img','choiceresponse','checkboxgroup','stringresponse','textline']:
                    print(f'❌ {fname}: Có thẻ lạ: {elem.tag}')
        print('✅ Kiểm tra sâu hoàn tất!')
    finally:
        shutil.rmtree(tmp)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Cách dùng: python deep_check_library_output.py file.tar.gz")
        exit(1)
    check_library_tar(sys.argv[1]) 