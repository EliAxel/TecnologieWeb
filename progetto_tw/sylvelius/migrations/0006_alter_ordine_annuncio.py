# Generated by Django 5.2.1 on 2025-05-25 15:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sylvelius', '0005_annuncio_is_published_alter_ordine_annuncio'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ordine',
            name='annuncio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ordini', to='sylvelius.annuncio'),
        ),
    ]
