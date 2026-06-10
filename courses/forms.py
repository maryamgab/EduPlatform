from django import forms
from .models import Course, Module, Lesson, LessonAttachment


class CourseForm(forms.ModelForm):
    AVATAR_COLORS = [("#334155", "Slate"), ("#6366f1", "Indigo"), ("#8b5cf6", "Purple"), ("#ec4899", "Pink"), ("#ef4444", "Red"), ("#f97316", "Orange"), ("#f59e0b", "Amber"), ("#10b981", "Green"), ("#06b6d4", "Cyan"),]
    avatar_color = forms.ChoiceField(label="Цвет аватара", choices=AVATAR_COLORS, widget=forms.RadioSelect,)
    access_code = forms.CharField(
        label="Код доступа",
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={"placeholder": "Нажмите «Сгенерировать код»","data-access-code-input": "",}
        ),
    )
    access_password_plain = forms.CharField(
        label="Пароль курса",
        required=False,
        widget=forms.PasswordInput(render_value=True, attrs={"placeholder": "Введите пароль для входа в курс"},),
    )

    class Meta:
        model = Course
        fields = ["title", "description", "avatar", "avatar_color", "category", "subcategory", "is_published", "is_private", "access_code",]
        labels = {"title": "Название", "description": "Описание", "avatar": "Аватар", "avatar_color": "Цвет аватара", "category": "Категория", "subcategory": "Подкатегория", "is_published": "Опубликовать курс", "is_private": "Сделать курс приватным", "access_code": "Код доступа",}
        widgets = {"category": forms.Select(attrs={"data-category-select": ""}), "subcategory": forms.Select(attrs={"data-subcategory-select": ""}),}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["subcategory"].required = False
        if self.instance and self.instance.pk:
            self.fields["access_code"].initial = self.instance.access_code or ""
        self.fields["access_password_plain"].help_text = (
            "Оставьте пустым, чтобы сохранить текущий пароль."
            if self.instance and self.instance.pk
            else "Пароль обязателен для приватного курса."
        )
        self.fields["category"].choices = [("", "Выберите категорию")] + list(Course.Category.choices)
        self.fields["subcategory"].choices = [("", "Сначала выберите категорию")]
        category = None
        if self.data.get("category"):
            category = self.data.get("category")
        elif self.instance and self.instance.pk:
            category = self.instance.category
        if category:
            subcategories = Course.get_subcategory_choices(category)
            self.fields["subcategory"].choices = [("", "Выберите подкатегорию")] + subcategories

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        subcategory = cleaned_data.get("subcategory")
        is_private = cleaned_data.get("is_private")
        access_code = Course.normalize_access_code(cleaned_data.get("access_code"))
        access_password_plain = (self.cleaned_data.get("access_password_plain") or "").strip()
        if subcategory:
            valid_subcategories = [value for value, _ in Course.get_subcategory_choices(category)]
            if subcategory not in valid_subcategories:
                self.add_error("subcategory", "Эта подкатегория не подходит для выбранной категории.")
        if is_private:
            if access_code and Course.objects.filter(access_code=access_code).exclude(pk=self.instance.pk).exists():
                self.add_error("access_code", "Такой код уже используется. Сгенерируйте другой.")
            has_existing_password = bool(getattr(self.instance, "access_password", ""))
            if not access_password_plain and not has_existing_password:
                self.add_error("access_password_plain", "Для приватного курса нужно указать пароль.")
        cleaned_data["access_code"] = access_code
        return cleaned_data

    def save(self, commit=True):
        course = super().save(commit=False)
        access_password_plain = (self.cleaned_data.get("access_password_plain") or "").strip()
        if course.is_private:
            course.access_code = self.cleaned_data.get("access_code") or Course.generate_unique_access_code()
            if access_password_plain:
                course.set_access_password(access_password_plain)
        else:
            course.access_code = None
            course.access_password = ""
        if commit:
            course.save()
            self.save_m2m()
        return course


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["title"]
        labels = {"title": "Название модуля"}


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title", "text", "video"]
        labels = {
            "title": "Название урока",
            "text": "Описание урока",
            "video": "Видео",
        }


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = LessonAttachment
        fields = ["title", "file"]
        labels = {
            "title": "Название файла",
            "file": "Файл",
        }
