from django.contrib import admin

# Register your models here.


from .models import (
    Assignment,
    AssignmentParticipant,
    AssignmentCycle,
    AssignmentCyclePair,
)

admin.site.register(Assignment)
admin.site.register(AssignmentCyclePair)
admin.site.register(AssignmentCycle)
admin.site.register(AssignmentParticipant)
