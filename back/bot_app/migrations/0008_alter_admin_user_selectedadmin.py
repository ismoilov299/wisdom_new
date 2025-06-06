# Generated by Django 5.0.2 on 2024-05-04 03:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot_app', '0007_admin'),
    ]

    operations = [
        migrations.AlterField(
            model_name='admin',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='bot_app.user'),
        ),
        migrations.CreateModel(
            name='SelectedAdmin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selected_admin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot_app.admin')),
            ],
            options={
                'verbose_name_plural': 'Selected Admins',
            },
        ),
    ]
