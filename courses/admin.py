from django.contrib import admin
from .forms import CourseForm
from .models import Course, Module, Lesson, LessonAttachment, Enrollment, LessonProgress


class LessonAttachmentInline(admin.TabularInline):
    model = LessonAttachment
    extra = 1


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    show_change_link = True


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseForm
    list_display = ("title", "category", "subcategory", "is_published", "created_at")
    list_filter = ("is_published", "category")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")
    list_filter = ("course",)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "order")
    list_filter = ("module__course",)
    inlines = [LessonAttachmentInline]


admin.site.register(LessonAttachment)
admin.site.register(Enrollment)
admin.site.register(LessonProgress)
