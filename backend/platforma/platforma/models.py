from django.conf import settings
from django.db import models
from django.utils import timezone


class Episode(models.Model):
    youtube_id = models.CharField(max_length=255)
    currently_downloading = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    draft_posted = models.BooleanField(default=False)
    deleted_old = models.BooleanField(default=False)
    first_seen = models.DateTimeField(null=True, auto_now_add=True)
    redownloaded = models.BooleanField(default=False)
    remote_filename = models.CharField(max_length=1000, null=True, blank=True)
    file_downloaded = models.BooleanField(default=False)
    deleted_by_uploader = models.BooleanField(default=False)

    def is_visible(self):
        return (
            not (self.deleted_old or self.hidden or self.currently_downloading)
            and self.file_downloaded
        )

    def get_filename(self):
        return f"{self.youtube_id}.mp3"

    def should_download(self):
        # returns true if the file is at least X hours old and is not
        # flagged as deleted by user
        tdelta = timezone.now() - self.first_seen
        enough_time_elapsed = int(tdelta.total_seconds()) > (
            settings.MIN_VIDEO_AGE_H * 60 * 60
        )
        return (
            not self.file_downloaded
            and enough_time_elapsed
            and not self.deleted_by_uploader
        )
