# Generated by Django 4.2.3 on 2023-07-23 17:49

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='QueueModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('queue_name', models.CharField(max_length=80)),
                ('attributes', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_ta', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]