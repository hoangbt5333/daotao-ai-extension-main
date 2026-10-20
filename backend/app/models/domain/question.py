"""
Question domain models
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


class QuestionType(Enum):
    """Question type enumeration"""
    MULTIPLE_CHOICE = "multiple_choice"
    MULTIPLE_SELECT = "multiple_select"
    TEXT_INPUT = "text_input"
    NUMERICAL = "numerical"
    TRUE_FALSE = "true_false"
    ESSAY = "essay"


class DifficultyLevel(Enum):
    """Question difficulty level"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class Question:
    """Question model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question: str = ""
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    choices: List[str] = field(default_factory=list)
    correct_answers: List[int] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    topic: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    points: float = 1.0
    image_url: Optional[str] = None
    explanation: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if isinstance(self.question_type, str):
            self.question_type = QuestionType(self.question_type)
        if isinstance(self.difficulty, str):
            self.difficulty = DifficultyLevel(self.difficulty)
    
    def add_choice(self, choice: str, is_correct: bool = False) -> None:
        """Add a choice to the question"""
        self.choices.append(choice)
        if is_correct:
            self.correct_answers.append(len(self.choices) - 1)
    
    def set_correct_answer(self, choice_index: int) -> None:
        """Set correct answer by choice index"""
        if 0 <= choice_index < len(self.choices):
            self.correct_answers = [choice_index]
    
    def set_multiple_correct_answers(self, choice_indices: List[int]) -> None:
        """Set multiple correct answers"""
        valid_indices = [i for i in choice_indices if 0 <= i < len(self.choices)]
        self.correct_answers = valid_indices
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the question"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the question"""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def is_correct(self, answer: Any) -> bool:
        """Check if the given answer is correct"""
        if self.question_type == QuestionType.MULTIPLE_CHOICE:
            return answer in self.correct_answers
        elif self.question_type == QuestionType.MULTIPLE_SELECT:
            return set(answer) == set(self.correct_answers)
        elif self.question_type == QuestionType.TEXT_INPUT:
            # For text input, we might need more sophisticated comparison
            return str(answer).strip().lower() == str(self.correct_answers[0]).strip().lower()
        elif self.question_type == QuestionType.NUMERICAL:
            try:
                return float(answer) == float(self.correct_answers[0])
            except (ValueError, TypeError):
                return False
        return False
    
    def validate(self) -> bool:
        """Validate question structure"""
        if not self.question:
            return False
        
        if self.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.MULTIPLE_SELECT]:
            if not self.choices:
                return False
            if not self.correct_answers:
                return False
            if max(self.correct_answers) >= len(self.choices):
                return False
        
        if self.question_type == QuestionType.MULTIPLE_CHOICE and len(self.correct_answers) != 1:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert question to dictionary"""
        return {
            "id": self.id,
            "question": self.question,
            "type": self.question_type.value,
            "choices": self.choices,
            "correct_answers": self.correct_answers,
            "tags": self.tags,
            "topic": self.topic,
            "difficulty": self.difficulty.value,
            "points": self.points,
            "image_url": self.image_url,
            "explanation": self.explanation,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        """Create question from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            question=data.get("question", ""),
            question_type=data.get("type", QuestionType.MULTIPLE_CHOICE),
            choices=data.get("choices", []),
            correct_answers=data.get("correct_answers", []),
            tags=data.get("tags", []),
            topic=data.get("topic"),
            difficulty=data.get("difficulty", DifficultyLevel.MEDIUM),
            points=data.get("points", 1.0),
            image_url=data.get("image_url"),
            explanation=data.get("explanation")
        )


@dataclass
class QuestionBank:
    """Question bank model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    questions: List[Question] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    organization: str = "SoDiTEC"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_question(self, question: Question) -> None:
        """Add a question to the bank"""
        self.questions.append(question)
    
    def remove_question(self, question_id: str) -> bool:
        """Remove a question from the bank"""
        for i, question in enumerate(self.questions):
            if question.id == question_id:
                self.questions.pop(i)
                return True
        return False
    
    def get_questions_by_tag(self, tag: str) -> List[Question]:
        """Get questions by tag"""
        return [q for q in self.questions if tag in q.tags]
    
    def get_questions_by_difficulty(self, difficulty: DifficultyLevel) -> List[Question]:
        """Get questions by difficulty level"""
        return [q for q in self.questions if q.difficulty == difficulty]
    
    def get_questions_by_type(self, question_type: QuestionType) -> List[Question]:
        """Get questions by type"""
        return [q for q in self.questions if q.question_type == question_type]
    
    def get_total_points(self) -> float:
        """Get total points of all questions"""
        return sum(q.points for q in self.questions)
    
    def validate(self) -> bool:
        """Validate question bank"""
        if not self.name:
            return False
        
        for question in self.questions:
            if not question.validate():
                return False
        
        return True 