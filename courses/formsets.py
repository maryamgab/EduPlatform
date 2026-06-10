from django.forms import inlineformset_factory
from .models import Lesson, LessonBlock
from .block_forms import LessonBlockForm

LessonBlockFormSet = inlineformset_factory(
    parent_model=Lesson,
    model=LessonBlock,
    form=LessonBlockForm,
    fields=["type", "order", "text", "file", "url"],
    extra=1,           # сколько пустых блоков показать сразу
    can_delete=True,   # возможность удалить блок на этой же странице
)