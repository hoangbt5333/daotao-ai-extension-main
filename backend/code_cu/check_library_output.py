import os
from lxml import etree

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../output-of-question-bank')
LIBRARY_XML = os.path.join(OUTPUT_DIR, 'library.xml')
PROBLEM_DIR = os.path.join(OUTPUT_DIR, 'problem')

# 1. Kiểm tra library.xml
print('--- Kiểm tra library.xml ---')
try:
    with open(LIBRARY_XML, encoding='utf-8') as f:
        xml = f.read()
    root = etree.fromstring(xml.encode('utf-8'))
    assert root.tag == 'library', 'Thẻ gốc phải là <library>'
    # Kiểm tra namespace các thẻ nsX
    ns_tags = [c.tag for c in root if c.tag.startswith('{http://code.edx.org/xblock/option}')]
    assert len(ns_tags) >= 8, 'Thiếu namespace option'
    # Kiểm tra thẻ <problem>
    problem_tags = [c for c in root if c.tag == 'problem']
    assert len(problem_tags) > 0, 'Không có thẻ <problem> nào trong library.xml'
    print('library.xml: OK')
except Exception as e:
    print(f'library.xml: LỖI - {e}')

# 2. Kiểm tra từng problem XML
print('\n--- Kiểm tra problem/*.xml ---')
err_count = 0
for fname in os.listdir(PROBLEM_DIR):
    if not fname.endswith('.xml'): continue
    fpath = os.path.join(PROBLEM_DIR, fname)
    try:
        with open(fpath, encoding='utf-8') as f:
            xml = f.read()
        root = etree.fromstring(xml.encode('utf-8'))
        assert root.tag == 'problem', f'{fname}: Thẻ gốc phải là <problem>'
        mcr = root.find('multiplechoiceresponse')
        assert mcr is not None, f'{fname}: Thiếu <multiplechoiceresponse>'
        cg = mcr.find('choicegroup')
        assert cg is not None, f'{fname}: Thiếu <choicegroup>'
        choices = cg.findall('choice')
        assert len(choices) >= 2, f'{fname}: <choicegroup> phải có >=2 <choice>'
        corrects = [c for c in choices if c.get('correct') == 'true']
        assert len(corrects) >= 1, f'{fname}: Phải có ít nhất 1 đáp án đúng (correct="true")'
        prompt = mcr.find('p[2]')
        assert prompt is not None and prompt.text and prompt.text.strip(), f'{fname}: Thiếu prompt câu hỏi'
        print(f'{fname}: OK')
    except Exception as e:
        print(f'{fname}: LỖI - {e}')
        err_count += 1

if err_count == 0:
    print('\nTất cả problem XML đều đạt chuẩn!')
else:
    print(f'\nCó {err_count} file problem XML bị lỗi!') 