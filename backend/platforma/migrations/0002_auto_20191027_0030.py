# Generated by Django 2.2.3 on 2019-10-27 00:30

import django.db.models.deletion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("platforma", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="assignmentcyclepair",
            name="assignment",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="platforma.Assignment",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="assignmentcyclepair",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="authored",
                to="platforma.AssignmentParticipant",
            ),
        ),
        migrations.AlterField(
            model_name="assignmentcyclepair",
            name="reviewer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="reviewed",
                to="platforma.AssignmentParticipant",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="assignmentcyclepair",
            unique_together={("reviewer", "assignment"), ("author", "assignment")},
        ),
        migrations.RemoveField(model_name="assignmentcyclepair", name="cycle"),
        migrations.DeleteModel(name="AssignmentCycle"),
    ]
