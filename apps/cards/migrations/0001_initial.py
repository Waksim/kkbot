# Generated by Django 5.2.3 on 2025-06-20 06:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=100, unique=True, verbose_name='Название тега')),
            ],
            options={
                'verbose_name': 'Тег',
                'verbose_name_plural': 'Теги',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Card',
            fields=[
                ('card_id', models.PositiveIntegerField(primary_key=True, serialize=False, verbose_name='ID карты')),
                ('card_type', models.CharField(choices=[('Character', 'Персонаж'), ('Action', 'Действие')], db_index=True, max_length=10, verbose_name='Тип карты')),
                ('name', models.CharField(db_index=True, max_length=255, verbose_name='Название')),
                ('title', models.CharField(blank=True, max_length=255, verbose_name='Подзаголовок')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('cost_info', models.JSONField(default=list, verbose_name='Информация о стоимости')),
                ('hp', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Здоровье')),
                ('is_new', models.BooleanField(db_index=True, default=False, verbose_name='Новая карта (еще не в релизе)')),
                ('related_card', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='character_card', to='cards.card', verbose_name='Связанная карта таланта/персонажа')),
                ('tags', models.ManyToManyField(blank=True, related_name='cards', to='cards.tag', verbose_name='Теги')),
            ],
            options={
                'verbose_name': 'Карта',
                'verbose_name_plural': 'Карты',
                'ordering': ['card_id'],
            },
        ),
    ]
