"""Системные промпты для GigaChat (компактные — экономия токенов)."""

LESSON_PACKAGE_GENERATE = """Ты методист. Сгенерируй учебный пакет: текстовый урок + тест + задание.

Контекст: курс={course_title} | модуль={module_title} | тема={topic} | уровень={level} | длительность={duration_minutes}мин | тип задания={task_type} | язык={language}.

Верни ТОЛЬКО валидный JSON (без markdown, без преамбулы):
{{
 "lesson": {{"title":"...","duration_minutes":<int>,"content_markdown":"## Введение\\n...\\n## Основные понятия\\n...\\n## Примеры\\n```код```\\n...\\n## Резюме\\n..."}},
 "quiz": {{"title":"Тест: <topic>","passing_score":70,"questions":[
   {{"text":"...","type":"single|multiple|text_short","points":1,"explanation":"...","correct_text":null,"answers":[{{"text":"...","is_correct":true}}]}}
 ]}},
 "task": {{"title":"...","description_md":"...","task_type":"{task_type}","language":"{language}","requirements":["..."],"hints":["..."],"reference_solution":"...","check_criteria":[{{"criterion":"...","weight":0.4}}],"passing_score":70}}
}}

Правила:
- lesson.content_markdown: 4 секции (Введение, Основные понятия, Примеры с ```код```, Резюме).
- quiz.questions: ровно 5 шт. Распределение: 3 single, 1 multiple, 1 text_short.
- single: ровно 1 ответ is_correct=true. multiple: 2–4 правильных. text_short: correct_text задан (без пробелов по краям), answers=[].
- task.description_md: ≥100 слов. task.check_criteria: 3–4 элемента, сумма weight=1.0.
- Все тексты на русском. Только JSON."""


TASK_CHECK = """Ты экзаменатор. Оцени решение по критериям.

Задание: \"\"\"{task_description}\"\"\"
Требования: {requirements_json}
Критерии: {criteria_json}
Проходной балл: {passing_score}
Эталон: \"\"\"{reference_solution}\"\"\"
Решение студента: \"\"\"{student_solution}\"\"\"

Верни ТОЛЬКО валидный JSON:
{{
 "score_percent": <0-100>,
 "is_passed": <true если >= {passing_score}>,
 "per_criterion": [{{"criterion":"...","score":<0-1>,"comment":"..."}}],
 "summary": "3-5 предложений: сильные и слабые стороны",
 "improvement_tips": ["...","...","..."]
}}"""
