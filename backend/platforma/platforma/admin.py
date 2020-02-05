from django.contrib import admin

from .models import (
    Assignment,
    AssignmentCycle,
    AssignmentCyclePair,
    AssignmentParticipant,
)

# Register your models here.


admin.site.register(Assignment)
admin.site.register(AssignmentCyclePair)
admin.site.register(AssignmentCycle)
admin.site.register(AssignmentParticipant)
