# Generated by Django 2.2.9 on 2020-02-06 13:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("platforma", "0005_episode_redownloaded"),
    ]

    operations = [
        migrations.AddField(
            model_name="episode",
            name="remote_filename",
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
    ]