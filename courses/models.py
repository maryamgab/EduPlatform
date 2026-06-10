from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from django.contrib.auth.hashers import check_password, make_password

import random
import secrets
import string

# модель курса
class Course(models.Model):
    # все категории
    class Category(models.TextChoices):
        PROGRAMMING = "programming", "Программирование"
        MATH = "math", "Высшая математика"
        DESIGN = "design", "Дизайн"
        SCHOOL_PROGRAM = "school_program", "Школьная программа"
        FOREIGN_LANG = "foreign_lang", "Иностранные языки"

    # все подкатегории
    class SubCategory(models.TextChoices):
        # программирование
        PYTHON = "python", "Python"
        JAVA = "java", "Java"
        CPP = "cpp", "C++"
        GO = "go", "Go"
        C = "c", "C"
        C_SHARP = "c_sharp", "C#"
        JAVA_SCRIPT = "java_script", "JavaScript"
        WEB = "web", "Web-разработка"
        HTML = "html", "HTML"
        CSS = "css", "CSS"
        FRONT = "front", "Frontend-разработка"

        # высшая математика
        LIN_ALGEBRA = "lin_algebra", "Линейная алгебра"
        DISCR_MATH = "discr_math", "Дискретная математика"
        MATH_ANALYS = "math_analys", "Математический анализ"
        DIFF_URAVN = "diff_uravn", "Дифференциальные уравнения"
        CHISL_METHODS = "chisl_methods", "Численные методы"
        URAVN_MATH_PHYSICS = "uravn_math_physics", "Уравнения математической физики"

        # дизайн
        UIUX = "uiux", "UI/UX"
        GRAPHIC = "graphic", "Графический дизайн"

        # школьная программа
        S_MATH = "s_math", "Математика"
        S_FOREIGN_LANG = "s_foreign_lang", "Иностранный язык"
        S_PROGRAMMING = "s_programming", "Информатика"
        S_BIOLOGY = "s_biology", "Биология"
        S_RUSSIAN = "s_russian", "Русский язык"
        S_GEOGRAPHY = "s_geography", "География"
        S_ECONOMY = "s_economy", "Экономика"
        S_HISTORY = "s_history", "История"
        S_SOCIAL_SCIENCE = "s_social_science", "Обществознание"
        S_PHYSICS = "s_physics", "Физика"

        # иностранные языки
        ENGLISH = "english", "Английский язык"
        GERMAN = "german", "Немецкий язык"
        FRENCH = "french", "Французский язык"
        SPANISH = "spanish", "Испанский язык"

    # словарь соответствия категории и подкатегории
    SUBCATEGORY_MAP = {
        Category.PROGRAMMING: [
            (SubCategory.PYTHON, SubCategory.PYTHON.label),
            (SubCategory.JAVA, SubCategory.JAVA.label),
            (SubCategory.CPP, SubCategory.CPP.label),
            (SubCategory.GO, SubCategory.GO.label),
            (SubCategory.C, SubCategory.C.label),
            (SubCategory.C_SHARP, SubCategory.C_SHARP.label),
            (SubCategory.JAVA_SCRIPT, SubCategory.JAVA_SCRIPT.label),
            (SubCategory.WEB, SubCategory.WEB.label),
            (SubCategory.HTML, SubCategory.HTML.label),
            (SubCategory.CSS, SubCategory.CSS.label),
            (SubCategory.FRONT, SubCategory.FRONT.label),
        ],
        Category.MATH: [
            (SubCategory.LIN_ALGEBRA, SubCategory.LIN_ALGEBRA.label),
            (SubCategory.DISCR_MATH, SubCategory.DISCR_MATH.label),
            (SubCategory.MATH_ANALYS, SubCategory.MATH_ANALYS.label),
            (SubCategory.DIFF_URAVN, SubCategory.DIFF_URAVN.label),
            (SubCategory.CHISL_METHODS, SubCategory.CHISL_METHODS.label),
            (SubCategory.URAVN_MATH_PHYSICS, SubCategory.URAVN_MATH_PHYSICS.label),
        ],
        Category.DESIGN: [
            (SubCategory.UIUX, SubCategory.UIUX.label),
            (SubCategory.GRAPHIC, SubCategory.GRAPHIC.label),
        ],
        Category.SCHOOL_PROGRAM: [
            (SubCategory.S_MATH, SubCategory.S_MATH.label),
            (SubCategory.S_FOREIGN_LANG, SubCategory.S_FOREIGN_LANG.label),
            (SubCategory.S_PROGRAMMING, SubCategory.S_PROGRAMMING.label),
            (SubCategory.S_BIOLOGY, SubCategory.S_BIOLOGY.label),
            (SubCategory.S_RUSSIAN, SubCategory.S_RUSSIAN.label),
            (SubCategory.S_GEOGRAPHY, SubCategory.S_GEOGRAPHY.label),
            (SubCategory.S_ECONOMY, SubCategory.S_ECONOMY.label),
            (SubCategory.S_HISTORY, SubCategory.S_HISTORY.label),
            (SubCategory.S_SOCIAL_SCIENCE, SubCategory.S_SOCIAL_SCIENCE.label),
            (SubCategory.S_PHYSICS, SubCategory.S_PHYSICS.label),
        ],
        Category.FOREIGN_LANG: [
            (SubCategory.ENGLISH, SubCategory.ENGLISH.label),
            (SubCategory.GERMAN, SubCategory.GERMAN.label),
            (SubCategory.FRENCH, SubCategory.FRENCH.label),
            (SubCategory.SPANISH, SubCategory.SPANISH.label),
        ],
    }


    # хранение всех нужных данных курса
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="owned_courses",)
    category = models.CharField(max_length=50, choices=Category.choices, blank=True, null=True, verbose_name="Категория",)
    subcategory = models.CharField(max_length=50, choices=SubCategory.choices, blank=True, null=True, verbose_name="Подкатегория",)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    avatar = models.FileField(upload_to="courses/avatars/", blank=True, null=True)
    avatar_color = models.CharField(max_length=20, blank=True)
    is_published = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False, verbose_name="Приватный курс")
    access_code = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Код доступа")
    access_password = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    # по умолчанию курсы сортируются по дате создания
    class Meta:
        ordering = ["-created_at"]

    # нормализация кода доступа
    @staticmethod
    def normalize_access_code(code: str) -> str:
        return "".join(ch for ch in (code or "").upper() if ch.isalnum())

    # генерация кода доступа
    @classmethod
    def generate_unique_access_code(cls, length: int = 8) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(length))
            if not cls.objects.filter(access_code=code).exists():
                return code

    # получение субкатегории для нужной категории
    @classmethod
    def get_subcategory_choices(cls, category):
        return cls.SUBCATEGORY_MAP.get(category, [])

    # установка пароля для приватного курса
    def set_access_password(self, raw_password: str):
        self.access_password = make_password(raw_password)

    # проверка пароля приватного курса
    def check_access_password(self, raw_password: str) -> bool:
        return bool(self.access_password and raw_password and check_password(raw_password, self.access_password))

    # сохранение курса (запись названия курса, установка цвета аватара по умолчанию, настройка кода и пароля для приватного курса)
    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "course"
            slug = base
            i = 2
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug

        if not self.avatar and not self.avatar_color:
            palette = [
                "#111827",
                "#1D4ED8",
                "#15803D",
                "#B91C1C",
                "#7C3AED",
                "#0F766E",
                "#C2410C",
                "#334155",
            ]
            self.avatar_color = random.choice(palette)

        if self.is_private:
            self.access_code = self.normalize_access_code(self.access_code)
            if not self.access_code:
                self.access_code = self.generate_unique_access_code()
        else:
            self.access_code = None
            self.access_password = ""

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# модель модуля курса (для деления курса на тематические части)
class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]
        unique_together = [("course", "order")]

    def __str__(self):
        return f"{self.course.title} — {self.title}"


# модель урока
class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    text = models.TextField(blank=True)
    video = models.FileField(upload_to="lessons/videos/", blank=True, null=True)

    class Meta:
        ordering = ["order"]
        unique_together = [("module", "order")]

    def __str__(self):
        return f"{self.module.course.title} — {self.title}"


# модель блока урока
class LessonBlock(models.Model):
    TEXT = "text"
    IMAGE = "image"
    GIF = "gif"
    AUDIO = "audio"
    VIDEO = "video"

    TYPE_CHOICES = [
        (TEXT, "Текст"),
        (IMAGE, "Картинка"),
        (GIF, "GIF"),
        (AUDIO, "Аудио"),
        (VIDEO, "Видео"),
    ]

    lesson = models.ForeignKey("Lesson", on_delete=models.CASCADE, related_name="blocks")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TEXT)
    order = models.PositiveIntegerField(default=1)
    text = models.TextField(blank=True)
    file = models.FileField(
        upload_to="lesson_blocks/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp", "gif", "mp3", "wav", "ogg", "m4a", "mp4", "webm", "mov"]
            )
        ],
    )
    url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.lesson} #{self.order} ({self.type})"

# модель вложении урока
class LessonAttachment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="attachments")
    title = models.CharField(max_length=200, blank=True)
    file = models.FileField(upload_to="lessons/files/")

    def __str__(self):
        return self.title or self.file.name

# модель записи пользователей на курс
class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "course")]

    def __str__(self):
        return f"{self.user} -> {self.course}"

# модель прогресса урока
class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = [("user", "lesson")]

# модель теста
class Quiz(models.Model):
    lesson = models.OneToOneField("Lesson", on_delete=models.CASCADE, related_name="quiz")
    title = models.CharField(max_length=255, default="Тест")
    is_published = models.BooleanField(default=True)
    available_from = models.DateTimeField("Открыт с", null=True, blank=True)
    deadline = models.DateTimeField("Дедлайн", null=True, blank=True)
    show_correct_answers = models.BooleanField(
        default=True,
        verbose_name="Показывать правильные ответы после прохождения"
    )

    def __str__(self):
        return f"Quiz for {self.lesson}"

# модель вопроса теста
class Question(models.Model):
    SINGLE = "single"
    MULTI = "multi"
    TEXT = "text"
    MATCH = "match"

    TYPE_CHOICES = [
        (SINGLE, "Выбор одного ответа"),
        (MULTI, "Выбор нескольких ответов"),
        (TEXT, "Ввод ответа"),
        (MATCH, "Соответствие"),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=1)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    prompt = models.TextField("Вопрос")
    correct_text = models.CharField(max_length=255, blank=True)
    text_case_sensitive = models.BooleanField(default=False)
    points = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Q{self.order} ({self.type})"

# модель варианта ответа
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

# модель пары на соответствие
class MatchPair(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="pairs")
    left_text = models.CharField(max_length=255)
    right_text = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.left_text} -> {self.right_text}"

# модель попытки прохождения теста
class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    created_at = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=0)
    is_late = models.BooleanField("Сдано после дедлайна", default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Attempt {self.user} {self.quiz} {self.score}/{self.max_score}"

# модель ответа пользователя
class Answer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choices = models.ManyToManyField(Choice, blank=True)
    text_value = models.CharField(max_length=255, blank=True)
    match_map = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(default=False)
    earned_points = models.IntegerField(default=0)