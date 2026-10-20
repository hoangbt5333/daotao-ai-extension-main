import os
import tarfile
import tempfile
import shutil
from lxml import etree
import filecmp

# Hàm giải nén tar.gz
def extract_tar(tar_path, out_dir):
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(out_dir)

# So sánh policies/assets.json
def compare_assets_json(path1, path2):
    with open(path1, encoding='utf-8') as f1, open(path2, encoding='utf-8') as f2:
        c1, c2 = f1.read().strip(), f2.read().strip()
        if c1 != c2:
            print(f"policies/assets.json khác nhau:\n{path1}: {c1}\n{path2}: {c2}")
        else:
            print("policies/assets.json: OK")

# So sánh XML (cấu trúc, thẻ, thuộc tính, thứ tự, namespace)
def compare_xml(file1, file2, label):
    with open(file1, encoding='utf-8') as f1, open(file2, encoding='utf-8') as f2:
        xml1 = etree.parse(f1)
        xml2 = etree.parse(f2)
        def walk(node1, node2, path=''):
            if node1.tag != node2.tag:
                print(f"{label}: Khác thẻ {path}: {node1.tag} vs {node2.tag}")
            if sorted(node1.attrib.keys()) != sorted(node2.attrib.keys()):
                print(f"{label}: Khác thuộc tính tại {path}/{node1.tag}: {node1.attrib} vs {node2.attrib}")
            for k in node1.attrib:
                if node1.attrib.get(k) != node2.attrib.get(k):
                    print(f"{label}: Giá trị thuộc tính khác tại {path}/{node1.tag}/{k}: {node1.attrib.get(k)} vs {node2.attrib.get(k)}")
            # So sánh số lượng thẻ con
            if len(node1) != len(node2):
                print(f"{label}: Số lượng thẻ con khác tại {path}/{node1.tag}: {len(node1)} vs {len(node2)}")
            # So sánh text
            t1 = (node1.text or '').strip()
            t2 = (node2.text or '').strip()
            if t1 != t2:
                if t1 or t2:
                    print(f"{label}: Text khác tại {path}/{node1.tag}: '{t1}' vs '{t2}'")
            # Đệ quy so sánh từng thẻ con
            for i, (c1, c2) in enumerate(zip(node1, node2)):
                walk(c1, c2, path + f'/{node1.tag}[{i}]')
        walk(xml1.getroot(), xml2.getroot())
        print(f"{label}: So sánh xong!")

# So sánh thư mục problem
def compare_problem_dirs(dir1, dir2):
    files1 = set(os.listdir(dir1))
    files2 = set(os.listdir(dir2))
    only1 = files1 - files2
    only2 = files2 - files1
    if only1:
        print(f"problem/ chỉ có ở thư mục 1: {only1}")
    if only2:
        print(f"problem/ chỉ có ở thư mục 2: {only2}")
    for fname in files1 & files2:
        compare_xml(os.path.join(dir1, fname), os.path.join(dir2, fname), f"problem/{fname}")

# Hàm chính
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Cách dùng: python compare_tar_libraries.py file1.tar.gz file2.tar.gz")
        exit(1)
    tar1, tar2 = sys.argv[1], sys.argv[2]
    tmp1, tmp2 = tempfile.mkdtemp(), tempfile.mkdtemp()
    try:
        extract_tar(tar1, tmp1)
        extract_tar(tar2, tmp2)
        # So sánh cấu trúc
        for fname in ['library.xml', 'policies/assets.json']:
            p1 = os.path.join(tmp1, fname)
            p2 = os.path.join(tmp2, fname)
            if not (os.path.exists(p1) and os.path.exists(p2)):
                print(f"Thiếu file {fname} ở một trong hai thư mục!")
        # So sánh library.xml
        compare_xml(os.path.join(tmp1, 'library.xml'), os.path.join(tmp2, 'library.xml'), 'library.xml')
        # So sánh policies/assets.json
        compare_assets_json(os.path.join(tmp1, 'policies/assets.json'), os.path.join(tmp2, 'policies/assets.json'))
        # So sánh problem
        compare_problem_dirs(os.path.join(tmp1, 'problem'), os.path.join(tmp2, 'problem'))
    finally:
        shutil.rmtree(tmp1)
        shutil.rmtree(tmp2) 