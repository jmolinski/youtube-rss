from django.db import models


class Assignment(models.Model):
    number = models.IntegerField()
    name = models.CharField(max_length=255)


class AssignmentParticipant(models.Model):
    email = models.EmailField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    assignment = models.ForeignKey(
        to=Assignment, on_delete=models.CASCADE, related_name="participants"
    )

    class Meta:
        unique_together = ["email", "assignment"]


class AssignmentCyclePair(models.Model):
    author = models.ForeignKey(
        to=AssignmentParticipant, on_delete=models.DO_NOTHING, related_name="authored"
    )
    reviewer = models.ForeignKey(
        to=AssignmentParticipant, on_delete=models.DO_NOTHING, related_name="reviewed"
    )
    assignment = models.ForeignKey(
        to=Assignment, on_delete=models.CASCADE, related_name="pairs"
    )

    class Meta:
        unique_together = [["author", "assignment"], ["reviewer", "assignment"]]
