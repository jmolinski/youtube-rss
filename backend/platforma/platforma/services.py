import json
import multiprocessing
import os
import subprocess
import xmlrpc
import xmlrpc.client

from datetime import datetime
from typing import Optional

from django.conf import settings

import requests

from platforma.platforma import models


def send_drafts():
    if not settings.DRAFTS_ENABLED:
        return

    # posortuj tak zeby najstarsze lecialy najpierw
    eps = models.Episode.objects.filter(draft_posted=False, currently_downloading=False)
    eps_dates = [(e, get_file_data(e.get_filename())["upload_date"]) for e in eps]
    eps = [e[0] for e in sorted(eps_dates, key=lambda x: x[1])]

    for ep in eps:
        if ep.is_visible():
            send_draft(ep)
            break  # TODO


def send_draft(episode: models.Episode):
    print("Submitting draft", episode.youtube_id)
    if episode.hidden or episode.draft_posted:
        print("Aborting sending draft for", episode.youtube_id)

    episode.hidden = True
    episode.save()

    client = xmlrpc.client.ServerProxy("http://nocneradio.pl/xmlrpc.php")
    ep_data = get_file_data(episode.get_filename())

    # upload image
    img_data: Optional[dict] = None
    thumbnail_url = ep_data["thumbnail"]
    if thumbnail_url:
        r = requests.get(thumbnail_url, stream=True)
        if r.status_code == 200:
            try:
                img_data = client.wp.uploadFile(
                    0,
                    settings.NR_USERNAME,
                    settings.NR_PASSWD,
                    {
                        "name": episode.youtube_id + "_img.jpg",
                        "type": "image/jpeg",
                        "bits": xmlrpc.client.Binary(r.content),
                    },
                )
                print("Uploaded thumbnail for", episode.youtube_id)
            except:
                print("Failed to upload thumbnail for", episode.youtube_id)

    # 2. create draft post
    try:
        date = f"{ep_data['day']:02d}.{ep_data['month']:02d}.{ep_data['year']:04}"
        original_title = ep_data["title"]
        current_time = datetime.today().strftime("%Y-%m-%d-%H:%M:%S")

        original_description = ep_data["description"].split("Donejty na")[
            0
        ]  # cut the footer about tipanddonation
        padded_description = (
            original_description + " \n\n" if original_description.strip() else ""
        )

        description = (
            f"[{date}] \n{padded_description}Wpis utworzony automatycznie na podstawie audycji"
            f" na youtube: https://www.youtube.com/watch?v={episode.youtube_id}\n\n"
            f"Identyfikator ###{episode.youtube_id} nr-yt==v0.0.1 {current_time}###\n"
        )
        content = {
            "post_type": "post",
            "post_title": original_title,
            # "post_excerpt": "test_excerpt",
            "post_content": description,
            "post_format": "standard",
            "custom_fields": [
                {
                    "key": "enclosure",
                    "value": f"https://nocneradio.xyz/feeds/media/{episode.youtube_id}.mp3\n\naudio/mpeg",
                },
            ],
        }
        if img_data and "attachment_id" in img_data:
            content["post_thumbnail"] = int(img_data["attachment_id"])
    except Exception as e:
        print("Problem preparing post data for draft", episode.youtube_id)
        print("Error datails:", str(e), repr(e))
        return

    try:
        client.wp.newPost(0, settings.NR_USERNAME, settings.NR_PASSWD, content)
    except Exception as e:
        print("Problem submitting draft post for", episode.youtube_id)
        print("Error datails:", str(e), repr(e))
    else:
        episode.draft_posted = True
        episode.hidden = False
        episode.save()


def download_video(id):
    if models.Episode.filter(youtube_id=id, currently_downloading=True).exists():
        print(f"Skipping {id} [the video is already being processed]")
        return -1
    if models.Episode.filter(youtube_id=id).exists():
        print(f"Skipping {id} [the video has already been processed or is obsolete]")
        return -2

    episode = models.Episode(youtube_id=id, currently_downloading=True)
    episode.save()
    try:
        ret = subprocess.call(
            [
                "youtube-dl",
                "-f",
                "bestaudio",
                "--extract-audio",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "128K",
                "--write-info-json",
                "--output",
                r"/app/shared/media/%(id)s.download.temp",
                f"https://www.youtube.com/watch?v={id}",
            ],
            shell=False,
        )
        subprocess.call(
            [
                "mv",
                f"/app/shared/media/{id}.download.temp.info.json",
                f"/app/shared/media/{id}.info.json",
            ],
            shell=False,
        )
        subprocess.call(
            [
                "mv",
                f"/app/shared/media/{id}.download.mp3",
                f"/app/shared/media/{id}.mp3",
            ],
            shell=False,
        )

        return ret
    except Exception as e:
        print(e)
        return 1
    finally:
        episode.currently_downloading = False
        episode.save()


def update_local():
    ## add local files to database -- TEMP #TODO

    for yt_id in get_saved_only_ids():
        if not models.Episode.objects.filter(youtube_id=yt_id).exists():
            models.Episode(youtube_id=yt_id, redownloaded=True).save()

    ## proceed
    get_ids_process = subprocess.run(
        [
            "youtube-dl",
            "--get-id",
            "--playlist-items",
            "1-" + str(settings.KEEP_LAST_N),
            "--skip-download",
            "--flat-playlist",
            r"https://www.youtube.com/channel/UCH1w8bpxhzR2ACjPE__PEkw/",
        ],
        capture_output=True,
    )
    ids_to_download = {
        i for i in get_ids_process.stdout.decode("utf-8").split("\n") if len(i) > 3
    }

    already_downloaded = {
        x.youtube_id
        for x in [y for y in models.Episode.objects.all() if y.is_visible()]
    }
    currently_downloading = {
        x.youtube_id
        for x in models.Episode.objects.filter(currently_downloading=True).all()
    }
    to_skip = ids_to_download & already_downloaded
    ids_to_download = ids_to_download - (already_downloaded | currently_downloading)

    print("Skipping already downloaded ids:", to_skip)
    if currently_downloading:
        print("Skipping currently downloading ids:", currently_downloading)

    if len(ids_to_download) > 5:
        print("Capping full list to download [", ids_to_download, "] to [", end=" ")
        ids_to_download = set(list(ids_to_download)[:5])
        print(ids_to_download, "] to not git 429 too many requests")

    if ids_to_download:
        pool = multiprocessing.Pool(processes=settings.CONCURRENT_DOWNLOADS)
        print(pool.map(download_video, list(ids_to_download)))
    else:
        print("Nothing to download")

    ######### clear old files

    saved_filenames = [
        y.get_filename() for y in models.Episode.objects.all() if y.is_visible()
    ]
    saved_videos = list(map(get_file_data, saved_filenames))
    if len(saved_videos) > settings.REMOVE_THRESHOLD_N:
        saved_videos.sort(key=lambda x: x["sortby"])
        vid = saved_videos[0]  # to_delete

        vid_path = os.path.join(
            "/app/shared/media/", vid["media_url"].split("media/")[1]
        )
        metadata_path = os.path.join("/app/shared/media/", vid["id"] + ".info.json")
        print("Removing:", vid_path, metadata_path)

        os.remove(vid_path)
        os.remove(metadata_path)
        episode = models.Episode.get(youtube_id=vid["id"])
        episode.deleted_old = True
        episode.save()


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
        "thumbnail": parsed_info.get("thumbnails", [{"url": "https://example.com"}])[0][
            "url"
        ],
        "extension": ext,
        "duration": parsed_info["duration"],
        "sortby": (parsed_info["upload_date"], parsed_info["duration"]),
        "year": yr,
        "month": mnth,
        "day": day,
    }
