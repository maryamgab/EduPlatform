
from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from .models import Quiz, Question, Choice, MatchPair


class QuizForm(forms.ModelForm):
    available_from = forms.DateTimeField(
        required=False,
        label="Открыт с",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    deadline = forms.DateTimeField(
        required=False,
        label="Дедлайн",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = Quiz
        fields = [
            "title",
            "is_published",
            "show_correct_answers",
            "available_from",
            "deadline",
        ]
        labels = {
            "title": "Название теста",
            "is_published": "Опубликовать тест",
            "show_correct_answers": "Показывать правильные ответы после прохождения",
            "available_from": "Открыт с",
            "deadline": "Дедлайн",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in ("available_from", "deadline"):
            value = getattr(self.instance, field_name, None)
            if value:
                value = timezone.localtime(value)
                self.initial[field_name] = value.strftime("%Y-%m-%dT%H:%M")

    def clean(self):
        cleaned_data = super().clean()
        available_from = cleaned_data.get("available_from")
        deadline = cleaned_data.get("deadline")

        if available_from and deadline and deadline < available_from:
            self.add_error("deadline", "Дедлайн не может быть раньше даты открытия теста.")

        return cleaned_data


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["order", "type", "prompt", "points", "correct_text", "text_case_sensitive"]
        labels = {
            "order": "Порядок",
            "type": "Тип вопроса",
            "prompt": "Вопрос",
            "points": "Баллы",
            "correct_text": "Правильный ответ",
            "text_case_sensitive": "Учитывать регистр",
        }
        widgets = {
            "correct_text": forms.TextInput(attrs={"placeholder": "Введите правильный ответ"}),
        }


ChoiceFormSet = inlineformset_factory(
    parent_model=Question,
    model=Choice,
    fields=["text", "is_correct"],
    extra=1,
    can_delete=True,
)

MatchPairFormSet = inlineformset_factory(
    parent_model=Question,
    model=MatchPair,
    fields=["left_text", "right_text"],
    extra=1,
    can_delete=True,
)


class ChoiceInlineForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ["text", "is_correct"]
        labels = {
            "text": "Текст",
            "is_correct": "Правильный",
        }


class MatchPairInlineForm(forms.ModelForm):
    class Meta:
        model = MatchPair
        fields = ["left_text", "right_text"]
        labels = {
            "left_text": "Левая часть",
            "right_text": "Правая часть",
        }