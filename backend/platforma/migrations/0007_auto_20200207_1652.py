# Generated by Django 2.2.9 on 2020-02-07 16:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("platforma", "0006_episode_remote_filename"),
    ]

    operations = [
        migrations.RemoveField(model_name="episode", name="download_date",),
        migrations.AddField(
            model_name="episode",
            name="file_downloaded",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="episode",
            name="first_seen",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
