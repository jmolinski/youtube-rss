from django.conf import settings
import multiprocessing
import subprocess
import os
import json
from platforma.platforma import models


def publish_episode(youtube_id):
    pass


def download_video(id):
    if models.Episode.filter(youtube_id=id, currently_downloading=True).exists():
        print(f"Skipping {id} [the video is already being processed]")
        return -1
    if models.Episode.filter(youtube_id=id).exists():
        print(f"Skipping {id} [the video has already been processed or is obsolete]")
        return -2

    try:
        episode = models.Episode(youtube_id=id, currently_downloading=True)
        episode.save()
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
