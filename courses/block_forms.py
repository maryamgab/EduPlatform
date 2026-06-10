from django import forms
from .models import LessonBlock

class LessonBlockForm(forms.ModelForm):
    class Meta:
        model = LessonBlock
        fields = ["type", "order", "text", "file", "url"]

        widgets = {
            "text": forms.Textarea(attrs={"class": "richtext", "rows": 6}),
        }

    def clean(self):
        cleaned = super().clean()
        t = cleaned.get("type")
        text = (cleaned.get("text") or "").strip()
        f = cleaned.get("file")
        url = (cleaned.get("url") or "").strip()

        if t == LessonBlock.TEXT:
            if not text:
                self.add_error("text", "Для текстового блока нужен текст.")
            # чтобы не было мусора
            cleaned["file"] = None
            cleaned["url"] = ""

        if t in (LessonBlock.IMAGE, LessonBlock.GIF, LessonBlock.AUDIO, LessonBlock.VIDEO):
            if not f and not url:
                self.add_error("file", "Загрузите файл или укажите ссылку.")
                self.add_error("url", "Укажите ссылку или загрузите файл.")
            if text:
                # можно запретить текст в медиа-блоках, или оставить как подпись — решай
                pass

        return cleaned