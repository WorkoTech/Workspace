# Generated by Django 3.0.1 on 2020-03-03 12:24

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_invitation_sender'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
