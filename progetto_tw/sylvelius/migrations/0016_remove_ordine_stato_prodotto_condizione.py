# Generated by Django 5.2.1 on 2025-05-30 19:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sylvelius', '0015_alter_prodotto_descrizione_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ordine',
            name='stato',
        ),
        migrations.AddField(
            model_name='prodotto',
            name='condizione',
            field=models.CharField(choices=[('nuovo', 'Nuovo'), ('usato', 'Usato')], default='nuovo', max_length=20),
        ),
    ]
