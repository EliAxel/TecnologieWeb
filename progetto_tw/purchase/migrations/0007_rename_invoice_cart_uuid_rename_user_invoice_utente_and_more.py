# Generated by Django 5.2.1 on 2025-06-22 16:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0006_alter_invoice_prodotto'),
        ('sylvelius', '0029_alter_annuncio_options_alter_prodotto_iva'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cart',
            old_name='invoice',
            new_name='uuid',
        ),
        migrations.RenameField(
            model_name='invoice',
            old_name='user',
            new_name='utente',
        ),
        migrations.AlterField(
            model_name='invoice',
            name='prodotto',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='sylvelius.prodotto'),
        ),
    ]
