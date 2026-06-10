from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Lesson, Question
from users.telegram import notify_new_lesson, notify_new_quiz_if_ready


@receiver(post_save, sender=Lesson)
def notify_about_new_lesson(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: notify_new_lesson(instance.pk))


@receiver(post_save, sender=Question)
def notify_about_new_quiz(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: notify_new_quiz_if_ready(instance.quiz_id))
