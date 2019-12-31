from django.conf import settings
from podgen import Podcast, Media, htmlencode
import multiprocessing
import subprocess
import datetime
import pytz
from django.http.response import HttpResponse
import os
import json


def download_video(id):
    try:
        return subprocess.call(
            [
                "youtube-dl",
                "-f",
                "bestaudio",
                "--write-info-json",
                "--output",
                r"/app/shared/media/%(id)s.%(ext)s",
                "https://www.youtube.com/watch?v=" + id,
            ],
            shell=False,
        )
    except Exception as e:
        print(e)
        return 1


def update_local(request):
    get_ids_process = subprocess.run(
        [
            "youtube-dl",
            "--get-id",
            "--playlist-items",
            "1-" + str(settings.KEEP_LAST_N),
            r"https://www.youtube.com/channel/UCH1w8bpxhzR2ACjPE__PEkw/",
        ],
        capture_output=True,
    )
    ids = [i for i in get_ids_process.stdout.decode("utf-8").split("\n") if len(i) > 3]
    pool = multiprocessing.Pool(processes=1)
    print(pool.map(download_video, ids))

    ######### clear old files

    saved_videos = list(map(get_file_data, get_saved_ids()))
    if len(saved_videos) > settings.REMOVE_THRESHOLD_N:
        saved_videos.sort(key=lambda x: x['sortby'])
        vid = saved_videos[0]  # to_delete

        vid_path = os.path.join('/app/shared/media/', vid['media_url'].split('media/')[1])
        metadata_path = os.path.join('/app/shared/media/', vid['id'] + '.info.json')
        print('Removing:', vid_path, metadata_path)

        os.remove(vid_path)
        os.remove(metadata_path)

    return HttpResponse("OK")


def create_nr_podcast():
    p = Podcast()
    p.name = "NocneRadio youtube"
    p.description = "Feed kanalu youtube nocnego radia"
    p.language = "pl"
    p.feed_url = "https://molinski.dev/feeds/nr/feed/"
    p.explicit = False
    p.complete = False
    p.new_feed_url = "https://molinski.dev/feeds/nr/feed/"
    p.website = "https://nocneradio.pl"

    return p


def add_episode(feed, video_data):
    print(video_data)
    e1 = feed.add_episode()
    e1.id = video_data["id"]
    e1.title = video_data["title"]
    e1.summary = htmlencode(video_data["description"])
    e1.image = video_data["thumbnail"]
    e1.publication_date = datetime.datetime(
        video_data["year"],
        video_data["month"],
        video_data["day"],
        12,
        0,
        0,
        tzinfo=pytz.utc,
    )
    e1.media = Media(
        video_data["media_url"],
        video_data["size"],
        type="audio/" + video_data["extension"],
        duration=datetime.timedelta(seconds=video_data["duration"]),
    )


def get_saved_ids():
    for root, dirs, files in os.walk("/app/shared/media/"):
        for file in files:
            if file.count(".") == 1:
                yield file


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
        "media_url": "https://molinski.dev/feeds/media/" + filename,
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


def get_rss_feed(request):
    nr = create_nr_podcast()
    ids = list(get_saved_ids())  # 'id.ext'

    for ep in ids:
        add_episode(nr, get_file_data(ep))

    return HttpResponse(nr.rss_str(), content_type="text/xml")
