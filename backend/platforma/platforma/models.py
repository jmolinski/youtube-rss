from django.db import models


class Episode(models.Model):
    youtube_id = models.CharField(max_length=255)
    currently_downloading = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    draft_posted = models.BooleanField(default=False)
    deleted_old = models.BooleanField(default=False)
    download_date = models.DateTimeField(null=True, default=None)
    redownloaded = models.BooleanField(default=False)

    def is_visible(self):
        return (
            self.youtube_id
            and (not self.currently_downloading)
            and (not self.hidden)
            and (not self.deleted_old)
        )

    def get_filename(self):
        return f"{self.youtube_id}.mp3"
