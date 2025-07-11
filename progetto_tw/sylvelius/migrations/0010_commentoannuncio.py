# Generated by Django 5.2.1 on 2025-05-28 10:07

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sylvelius', '0009_alter_annuncio_prodotto'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CommentoAnnuncio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('testo', models.TextField()),
                ('rating', models.IntegerField(help_text='Valutazione da 0 a 5', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('data_pubblicazione', models.DateTimeField(auto_now_add=True)),
                ('annuncio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commenti', to='sylvelius.annuncio')),
                ('utente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commenti_annunci', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
