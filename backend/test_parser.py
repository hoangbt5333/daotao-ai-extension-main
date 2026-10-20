#!/usr/bin/env python3
"""
Test script for question parsing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import re

def test_parse():
    # Test case 1: (x) marker
    questions_text_1 = '''Đối với gói thầu có giá không quá 50 triệu đồng, khẳng định nào sau đây là đúng?
(!) Phải lập kế hoạch lựa chọn nhà thầu nhưng không cần ký hợp đồng.
( ) Không cần lập kế hoạch lựa chọn nhà thầu và không cần hóa đơn, chứng từ.
(x) Không cần lập kế hoạch lựa chọn nhà thầu nhưng phải đảm bảo đủ hóa đơn, chứng từ.
( ) Bắt buộc phải ký hợp đồng với nhà cung cấp.'''

    # Test case 2: (!x) marker
    questions_text_2 = '''Generative AI tập trung vào việc phát triển các mô hình có khả năng nào?
(!x) Tự động tạo ra dữ liệu mới, sáng tạo nội dung mới dựa trên dữ liệu hiện có.
( ) Học từ dữ liệu đã có và tái tạo lại dữ liệu đó một cách chính xác.
( ) Phân tích dữ liệu hiện có và đưa ra dự đoán về tương lai.
( ) Tối ưu hóa các thuật toán học máy để tăng hiệu suất.'''

    # Test case 3: Real user input with de tags
    questions_text_3 = '''de0
Generative AI tập trung vào việc phát triển các mô hình có khả năng nào?
(!) Học từ dữ liệu đã có và tái tạo lại dữ liệu đó một cách chính xác.
( ) Phân tích dữ liệu hiện có và đưa ra dự đoán về tương lai.
(x) Tự động tạo ra dữ liệu mới, sáng tạo nội dung mới dựa trên dữ liệu hiện có.
( ) Tối ưu hóa các thuật toán học máy để tăng hiệu suất.
Mô hình AI nào sau đây được dùng để chuyển văn bản thành hình ảnh?
(!) ChatGPT.
( ) Gemini.
(x) DALL-E của OpenAI.
( ) TurboScribe.'''

    def parse_questions(questions_text):
        """Parser for new format: Question with (!), ( ), (x), (!x) markers"""
        questions = []
        
        # Split into lines and process
        lines = [l.strip() for l in questions_text.strip().split('\n') if l.strip()]
        
        current_question = None
        current_choices = []
        current_correct_answer = None
        
        for line in lines:
            # Check if line starts with marker pattern
            marker_match = re.match(r'^[\(\)!x\s]+', line)
            
            if not marker_match:
                # This is a question line (no markers)
                # If we have a previous question, save it
                if current_question and current_choices and current_correct_answer is not None:
                    questions.append({
                        "question": current_question,
                        "type": "multiple_choice",
                        "choices": current_choices,
                        "correct_answers": [current_correct_answer],
                        "tags": [],
                        "topic": "",
                        "is_valid": True,
                        "errors": []
                    })
                
                # Start new question
                current_question = line.strip()
                current_choices = []
                current_correct_answer = None
            else:
                # This is a choice line with markers
                # Extract the choice text (remove the marker)
                choice_text = re.sub(r'^[\(\)!x\s]+', '', line).strip()
                if choice_text:  # Only add if there's actual text
                    current_choices.append(choice_text)
                    
                    # Check if this is the correct answer
                    # (!x) = đáp án đầu tiên VÀ đúng
                    # (x) = đáp án đúng (không phải đầu tiên)
                    if '(!x)' in line:
                        current_correct_answer = len(current_choices) - 1  # 0-based index
                    elif '(x)' in line:
                        current_correct_answer = len(current_choices) - 1  # 0-based index
        
        # Don't forget the last question
        if current_question and current_choices and current_correct_answer is not None:
            questions.append({
                "question": current_question,
                "type": "multiple_choice",
                "choices": current_choices,
                "correct_answers": [current_correct_answer],
                "tags": [],
                "topic": "",
                "is_valid": True,
                "errors": []
            })
        
        return questions

    print("=== Test case 1: (x) marker ===")
    questions1 = parse_questions(questions_text_1)
    for i, q in enumerate(questions1):
        print(f'Question {i+1}: {q["question"]}')
        print(f'Choices: {q["choices"]}')
        print(f'Correct answer index: {q["correct_answers"]}')
        print(f'Correct answer text: {q["choices"][q["correct_answers"][0]] if q["correct_answers"] else None}')
        print()

    print("=== Test case 2: (!x) marker ===")
    questions2 = parse_questions(questions_text_2)
    for i, q in enumerate(questions2):
        print(f'Question {i+1}: {q["question"]}')
        print(f'Choices: {q["choices"]}')
        print(f'Correct answer index: {q["correct_answers"]}')
        print(f'Correct answer text: {q["choices"][q["correct_answers"][0]] if q["correct_answers"] else None}')
        print()

    print("=== Test case 3: Real user input with de tags ===")
    questions3 = parse_questions(questions_text_3)
    for i, q in enumerate(questions3):
        print(f'Question {i+1}: {q["question"]}')
        print(f'Choices: {q["choices"]}')
        print(f'Correct answer index: {q["correct_answers"]}')
        print(f'Correct answer text: {q["choices"][q["correct_answers"][0]] if q["correct_answers"] else None}')
        print()

if __name__ == "__main__":
    test_parse() 