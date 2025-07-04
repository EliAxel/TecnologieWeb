# Generated by Django 5.2.1 on 2025-05-24 14:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sylvelius', '0004_remove_annuncio_immagine_immagineannuncio'),
    ]

    operations = [
        migrations.AddField(
            model_name='annuncio',
            name='is_published',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='ordine',
            name='annuncio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='ordini', to='sylvelius.annuncio'),
        ),
    ]
