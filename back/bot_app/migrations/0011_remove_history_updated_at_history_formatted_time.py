# Generated by Django 5.0.2 on 2024-05-31 23:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot_app', '0010_history'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='history',
            name='updated_at',
        ),
        migrations.AddField(
            model_name='history',
            name='formatted_time',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
    ]
