from django.conf import settings
from podgen import Podcast, Media, htmlencode
import multiprocessing
import subprocess
import datetime
import pytz
from django.http.response import HttpResponse
import os
import json
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime


def download_video(id):
    try:
        return subprocess.call(
            [
                "youtube-dl",
                "-f",
                "bestaudio",
                "--extract-audio",
                "--audio-format",
                "mp3",
                "--audio-quality 128K",
                "--write-info-json",
                "--output",
                r"/app/shared/media/%(id)s.%(ext)s.download",
                "--exec",
                f'"mv /app/shared/media/{id}.mp3.download /app/shared/media/{id}.mp3 && rm -f /app/shared/media/{id}.webm.download"',
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
            "--skip-download",
            "--flat-playlist",
            r"https://www.youtube.com/channel/UCH1w8bpxhzR2ACjPE__PEkw/",
        ],
        capture_output=True,
    )
    ids_to_download = {
        i for i in get_ids_process.stdout.decode("utf-8").split("\n") if len(i) > 3
    }
    already_downloaded = {x["id"] for x in map(get_file_data, get_saved_ids())}

    to_skip = ids_to_download & already_downloaded
    ids_to_download = ids_to_download - already_downloaded

    print("Skipping already downloaded ids:", to_skip)

    if len(ids_to_download) > 5:
        print("Capping full list to download [", ids_to_download, "] to [", end=" ")
        ids_to_download = set(list(ids_to_download)[:5])
        print(ids_to_download, "] to not git 429 too many requests")

    if ids_to_download:
        pool = multiprocessing.Pool(processes=2)
        print(pool.map(download_video, list(ids_to_download)))

    ######### clear old files

    saved_videos = list(map(get_file_data, get_saved_ids()))
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

    return HttpResponse("OK")


def create_nr_podcast(extra):
    p = Podcast()
    p.name = extra["name"]
    p.description = "Feed kanalu youtube nocnego radia"
    p.language = "pl"
    p.feed_url = settings.NR_FEED_DOMAIN + "feeds/nr/feed/" + extra["url"]
    p.explicit = False
    p.complete = False
    p.new_feed_url = settings.NR_FEED_DOMAIN + "feeds/nr/feed/"
    p.website = "https://nocneradio.pl"
    p.image = "https://patronite.pl/upload/user/84115/okladka.jpg?1513161024"

    return p


def audio_format_to_mime(fmt):
    if fmt == "mp3":
        return "audio/mpeg"
    return "audio/" + fmt


def add_episode(feed, video_data):
    e1 = feed.add_episode()
    e1.id = video_data["id"]
    e1.title = video_data["title"]
    if "parsed_description" in video_data:
        e1.summary = video_data["parsed_description"]
    else:
        e1.summary = htmlencode(video_data["description"])
    e1.image = video_data["thumbnail"]
    if "exact_date" in video_data:
        e1.publication_date = video_data["exact_date"]
    else:
        e1.publication_date = datetime.datetime(
            video_data["year"],
            video_data["month"],
            video_data["day"],
            12,
            0,
            0,
            tzinfo=pytz.utc,
        )
    if "duration" in video_data:
        e1.media = Media(
            video_data["media_url"],
            video_data["size"],
            type=audio_format_to_mime(video_data["extension"]),
            duration=datetime.timedelta(seconds=video_data["duration"]),
        )
    else:
        e1.media = Media(
            video_data["media_url"],
            video_data["size"],
            type=audio_format_to_mime(video_data["extension"]),
        )


def get_saved_ids():
    for root, dirs, files in os.walk("/app/shared/media/"):
        for file in files:
            if file.count(".") == 1 and "download" not in file:
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


def parse_raw_nr_item(item):
    enclosure = item.find("enclosure")
    media_url = enclosure.get("url")
    filesize = int(enclosure.get("length"))
    date = item.find("pubDate").text

    return {
        "media_url": media_url,
        "size": filesize,
        "id": media_url,
        "title": item.find("title").text,
        "url": media_url,
        "filesize_raw": filesize,
        "parsed_description": item.find("description").text,
        "thumbnail": item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image").get(
            "href"
        ),
        "extension": "mp3",
        "sortby": 0,
        "exact_date": parsedate_to_datetime(date),
    }


def get_radio_feed():
    try:
        data = requests.get("http://nocneradio.pl/feed/")
        root = ET.fromstring(data.content.decode("utf-8"))

        raw_items = [x for x in root.find("channel").getchildren() if x.tag == "item"]
        for item in raw_items:
            try:
                yield parse_raw_nr_item(item)
            except Exception as e:
                print(e)
    except:
        pass


def get_rss_feed(request):
    nr = create_nr_podcast({"url": "", "name": "Nocne Radio YouTube Channel"})
    ids = list(get_saved_ids())  # 'id.ext'

    for ep in ids:
        add_episode(nr, get_file_data(ep))

    return HttpResponse(nr.rss_str(), content_type="text/xml")


def get_combined_rss_feed(request):
    nr = create_nr_podcast({"url": "combined/", "name": "Nocne Radio (+ YouTube)"})
    ids = list(get_saved_ids())  # 'id.ext'

    for ep in ids:
        add_episode(nr, get_file_data(ep))

    for ep in get_radio_feed():
        add_episode(nr, ep)

    return HttpResponse(nr.rss_str(), content_type="text/xml")
