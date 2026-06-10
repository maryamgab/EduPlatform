from django.urls import path
from . import views

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("courses/private/access/", views.private_course_access, name="private_course_access"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("courses/<slug:slug>/enroll/", views.enroll, name="enroll"),
    path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("lessons/<int:lesson_id>/complete/", views.complete_lesson, name="complete_lesson"),
    path("lessons/<int:lesson_id>/blocks/", views.lesson_blocks_manage, name="lesson_blocks_manage"),
    path("me/", views.me_dashboard, name="me_dashboard"),
    path("me/courses/create/", views.course_create, name="course_create"),
    path("me/courses/<int:course_id>/edit/", views.course_edit, name="course_edit"),
    path("me/courses/<int:course_id>/modules/add/", views.module_add, name="module_add"),
    path("me/modules/<int:module_id>/lessons/add/", views.lesson_add, name="lesson_add"),
    path("me/lessons/<int:lesson_id>/attachments/add/", views.attachment_add, name="attachment_add"),
    path("blocks/<int:block_id>/edit/", views.lesson_block_edit, name="lesson_block_edit"),
    path("blocks/<int:block_id>/delete/", views.lesson_block_delete, name="lesson_block_delete"),
    path("me/modules/<int:module_id>/lessons/create/", views.lesson_create_with_blocks, name="lesson_create_with_blocks"),
    path("me/lessons/<int:lesson_id>/quiz/", views.quiz_manage, name="quiz_manage"),
    path("me/quizzes/<int:quiz_id>/questions/add/", views.question_create, name="question_create"),
    path("me/questions/<int:question_id>/edit/", views.question_edit, name="question_edit"),
    path("me/questions/<int:question_id>/delete/", views.question_delete, name="question_delete"),
    path("lessons/<int:lesson_id>/quiz/", views.quiz_take, name="quiz_take"),
    path("lesson/<int:lesson_id>/quiz/attempts/",views.quiz_attempts,name="quiz_attempts",),
    path("quiz/attempt/<int:attempt_id>/",views.quiz_attempt_detail,name="quiz_attempt_detail",),
    path("me/lessons/<int:lesson_id>/quiz/results/",views.quiz_students_results, name="quiz_students_results",),
    path("me/quiz-attempts/<int:attempt_id>/",views.quiz_student_attempt_detail,name="quiz_student_attempt_detail",),
    path("me/course/<slug:slug>/students-progress/",views.course_students_progress,name="course_students_progress",),
    path("me/lessons/<int:lesson_id>/delete/", views.lesson_delete, name="lesson_delete"),
    path("me/courses/<int:course_id>/delete/", views.course_delete, name="course_delete"),
    path("me/lessons/<int:lesson_id>/move/<str:direction>/", views.lesson_move, name="lesson_move"),
]


