# Generated manually for private course access support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0009_quiz_available_from_quiz_deadline_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='access_code',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='Код доступа'),
        ),
        migrations.AddField(
            model_name='course',
            name='access_password',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='course',
            name='is_private',
            field=models.BooleanField(default=False, verbose_name='Приватный курс'),
        ),
    ]
