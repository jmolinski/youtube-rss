import json
import os

from django.conf import settings
from platforma.platforma import models
from django.shortcuts import get_object_or_404


def audio_format_to_mime(fmt):
    if fmt == "mp3":
        return "audio/mpeg"
    return "audio/" + fmt


def get_saved_only_ids():
    for root, dirs, files in os.walk("/app/shared/media/"):
        for file in files:
            if file.count(".") == 1 and "download" not in file:
                yield file.split(".")[0]


def get_file_data(filename):
    video_id, ext = filename.split(".")

    path_vid, path_info = (
        os.path.join("/app/shared/media", filename),
        os.path.join("/app/shared/media", video_id + ".info.json"),
    )

    with open(path_info) as info_f:
        parsed_info = json.loads(info_f.read())

    x = parsed_info["upload_date"]
    yr, mnth, day = map(int, [x[:4], x[4:6], x[6:]])

    raw_thumbnail = parsed_info.get("thumbnails", [{"url": "https://example.com"}])[0][
        "url"
    ]
    thumbnail = (
        raw_thumbnail
        if ".jpg" not in raw_thumbnail
        else (raw_thumbnail.split(".jpg")[0] + ".jpg")
    )
    thumbnail = thumbnail.replace("hqdefault.jpg", "maxresdefault.jpg")

    return {
        "media_url": settings.NR_FEED_DOMAIN + "feeds/media/" + filename,
        "size": os.path.getsize(path_vid),
        "id": video_id,
        "title": parsed_info["title"],
        "upload_date": parsed_info["upload_date"],
        "url": parsed_info["webpage_url"],
        "filesize_raw": parsed_info["filesize"],
        "filltitle": parsed_info["fulltitle"],
        "channel_id": parsed_info["channel_id"],
        "description": parsed_info["description"],
        "thumbnail": thumbnail,
        "extension": ext,
        "duration": parsed_info["duration"],
        "sortby": (parsed_info["upload_date"], parsed_info["duration"]),
        "year": yr,
        "month": mnth,
        "day": day,
        "tags": parsed_info.get("tags", []),
    }


def remove_file_and_mark_as_to_download(youtube_id: str) -> bool:
    episode = get_object_or_404(models.Episode, youtube_id=youtube_id)

    if not episode or not episode.file_downloaded:
        return False

    remove_episode_files(episode)
    episode.file_downloaded = False
    episode.draft_posted = False
    episode.save()

    return True


def remove_episode_files(episode: models.Episode) -> None:
    vid_path = os.path.join("/app/shared/media/", episode.youtube_id + ".mp3")
    metadata_path = os.path.join(
        "/app/shared/media/", episode.youtube_id + ".info.json"
    )
    print("Removing video:", vid_path, metadata_path)

    os.remove(vid_path)
    os.remove(metadata_path)
