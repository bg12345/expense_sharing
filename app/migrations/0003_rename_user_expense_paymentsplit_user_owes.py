# Generated by Django 5.0.6 on 2024-05-17 15:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_rename_split_amount_paymentsplit_user_expense'),
    ]

    operations = [
        migrations.RenameField(
            model_name='paymentsplit',
            old_name='user_expense',
            new_name='user_owes',
        ),
    ]
