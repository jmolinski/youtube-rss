import multiprocessing
import os
import random
import subprocess

from django.conf import settings

from platforma.platforma import models
from platforma.platforma.services import get_file_data


def download_video_call_ytdl(video_id: str):
    ret = subprocess.call(
        [
            "youtube-dl",
            "-f",
            "bestaudio",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "96K",
            "--write-info-json",
            "--verbose",
            "--output",
            r"/app/shared/media/%(id)s.download.temp",
            f"https://www.youtube.com/watch?v={video_id}",
        ],
        shell=False,
    )
    subprocess.call(
        [
            "mv",
            f"/app/shared/media/{video_id}.download.temp.info.json",
            f"/app/shared/media/{video_id}.info.json",
        ],
        shell=False,
    )
    subprocess.call(
        [
            "mv",
            f"/app/shared/media/{video_id}.download.mp3",
            f"/app/shared/media/{video_id}.mp3",
        ],
        shell=False,
    )

    return ret


def download_video(episode: models.Episode):
    episode.refresh_from_db()
    id = episode.youtube_id
    if episode.currently_downloading:
        print(f"Skipping {id} [the video is already being processed]")
        return -1
    if episode.is_visible() or not episode.should_download():
        print(f"Skipping {id} [the video has already been processed or is too young]")
        return -2

    episode.currently_downloading = True
    episode.save()
    try:
        ret = download_video_call_ytdl(episode.youtube_id)

        if int(ret) == 0:
            episode.file_downloaded = True
            episode.save()

        return ret
    except Exception as e:
        print(e)
        return 1
    finally:
        episode.currently_downloading = False
        episode.save()


def get_new_videos_and_add_to_database():
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

    for i in ids_to_download:
        if not models.Episode.objects.filter(youtube_id=i).exists():
            episode = models.Episode(youtube_id=i)
            episode.save()


def remove_obsolete_files():
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
        print("Removing obsolete video:", vid_path, metadata_path)

        os.remove(vid_path)
        os.remove(metadata_path)
        episode = models.Episode.objects.get(youtube_id=vid["id"])
        episode.deleted_old = True
        episode.save()


def update_local():
    get_new_videos_and_add_to_database()

    eps_to_download = [
        e
        for e in models.Episode.objects.filter(
            file_downloaded=False, currently_downloading=False, deleted_old=False
        )
        if e.should_download()
    ]

    if len(eps_to_download) > 5:
        print(
            "Capping full list to download [",
            [e.youtube_id for e in eps_to_download],
            "] to [",
            end=" ",
        )
        eps_to_download = set(random.shuffle(eps_to_download)[:5])
        print(
            [e.youtube_id for e in eps_to_download],
            "] to not get 429 too many requests",
        )

    if eps_to_download:
        pool = multiprocessing.Pool(processes=settings.CONCURRENT_DOWNLOADS)
        print(pool.map(download_video, list(eps_to_download)))
    else:
        print("Nothing to download")

    remove_obsolete_files()
