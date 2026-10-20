import os
from lxml import etree

# Các thẻ con hợp lệ trong problem XML
VALID_TAGS = set([
    'multiplechoiceresponse', 'choiceresponse', 'stringresponse',
    'p', 'h3', 'label', 'img', 'choicegroup', 'checkboxgroup', 'choice', 'textline'
])
REQUIRED_PROBLEM_ATTRS = {'display_name', 'tags', 'markdown'}

# Các thuộc tính bắt buộc của <library>
REQUIRED_LIBRARY_ATTRS = {
    'url_name', 'xblock-family', 'tags', 'display_name', 'course_edit_method', 'days_early_for_beta',
    'due', 'edxnotes', 'graceperiod', 'graded', 'group_access', 'in_entrance_exam', 'max_attempts',
    'rerandomize', 'self_paced', 'show_correctness', 'show_reset_button', 'showanswer', 'start',
    'static_asset_path', 'use_latex_compiler', 'user_partitions', 'video_auto_advance', 'video_bumper',
    'video_speed_optimizations', 'visible_to_staff_only', 'hide_from_toc', 'chapters', 'org', 'library'
}
# Các thẻ namespace hợp lệ
NAMESPACE_TAGS = [
    'ns0:name', 'ns1:giturl', 'ns2:matlab_api_key', 'ns3:xqa_key', 'ns4:chrome',
    'ns5:default_tab', 'ns6:format', 'ns7:source_file', 'ns8:advanced_modules'
]

def ns_tag(tag):
    prefix, name = tag.split(':')
    ns_uri = "http://code.edx.org/xblock/option"
    return f"{{{ns_uri}}}{name}"

def check_problem_xml_structure(xml):
    for attr in REQUIRED_PROBLEM_ATTRS:
        assert attr in xml.attrib, f"Thiếu thuộc tính {attr} trong <problem>"
    def _check(e, path="/"):
        if e.tag not in VALID_TAGS and e.tag != 'problem':
            return f"Thẻ không hợp lệ tại {path}: {e.tag}"
        for c in e:
            res = _check(c, path + f"{e.tag}/")
            if res:
                return res
        return None
    return _check(xml)

def check_library_xml_structure(xml):
    for attr in REQUIRED_LIBRARY_ATTRS:
        assert attr in xml.attrib, f"Thiếu thuộc tính {attr} trong <library>"
    children = list(xml)
    for i, tag in enumerate(NAMESPACE_TAGS):
        expected_tag = ns_tag(tag)
        assert children[i].tag == expected_tag, f"Thẻ con thứ {i+1} phải là {tag}, thực tế: {children[i].tag}"
        # KHÔNG kiểm tra xmlns:nsX trong .attrib nữa!
    for c in children[len(NAMESPACE_TAGS):]:
        assert c.tag == 'problem', f"Thẻ con sau namespace phải là <problem>, thực tế: {c.tag}"
    return None

def test_library_xml_structure():
    with open("output-of-question-bank/library.xml", encoding="utf-8") as f:
        xml2 = etree.fromstring(f.read().encode("utf-8"))
    # Kiểm tra cấu trúc sâu
    err = check_library_xml_structure(xml2)
    assert not err, f"library.xml không hợp lệ: {err}"
    # Kiểm tra tính nhất quán số lượng problem
    problems2 = xml2.findall("problem")
    problem_files = os.listdir("output-of-question-bank/problem")
    assert len(problems2) == len(problem_files), f"Số lượng <problem> trong library.xml ({len(problems2)}) không khớp số file problem/ ({len(problem_files)})"
    print(f"Số lượng <problem> và file problem/ nhất quán: {len(problems2)}")

def test_problem_xml_structure():
    for fname in sorted(os.listdir("output-of-question-bank/problem")):
        with open(f"output-of-question-bank/problem/{fname}", encoding="utf-8") as f:
            xml2 = etree.fromstring(f.read().encode("utf-8"))
        err = check_problem_xml_structure(xml2)
        assert not err, f"problem xml không hợp lệ: {fname}: {err}"
        print(f"problem/{fname}: OK")

if __name__ == "__main__":
    print("=== Bắt đầu test cấu trúc XML linh động ===")
    try:
        test_library_xml_structure()
        test_problem_xml_structure()
        print("Tất cả test cấu trúc XML đều PASSED!")
    except Exception as e:
        import traceback
        print("ĐÃ CÓ LỖI XẢY RA:")
        traceback.print_exc()