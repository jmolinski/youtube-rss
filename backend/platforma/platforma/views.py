from django.conf import settings
from podgen import Podcast, Media, htmlencode
import datetime
import pytz
from django.http.response import HttpResponse
import os
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from platforma.platforma import models
from platforma.platforma import services


def update_local(request):
    services.update_local()
    return HttpResponse("OK")


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
            type=services.audio_format_to_mime(video_data["extension"]),
            duration=datetime.timedelta(seconds=video_data["duration"]),
        )
    else:
        e1.media = Media(
            video_data["media_url"],
            video_data["size"],
            type=services.audio_format_to_mime(video_data["extension"]),
        )


def get_saved_ids():
    for root, dirs, files in os.walk("/app/shared/media/"):
        for file in files:
            if file.count(".") == 1 and "download" not in file:
                yield file


def get_saved_only_ids():
    for root, dirs, files in os.walk("/app/shared/media/"):
        for file in files:
            if file.count(".") == 1 and "download" not in file:
                yield file.split(".")[0]


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
    p.image = "https://patronite.pl/upload/user/84115/okladka.jpg"

    return p


def get_rss_feed(request):
    nr = create_nr_podcast({"url": "", "name": "Nocne Radio YouTube Channel"})
    ids = [y.get_filename() for y in models.Episode.objects.all() if y.is_visible()]

    for ep in ids:
        add_episode(nr, services.get_file_data(ep))

    return HttpResponse(nr.rss_str(), content_type="text/xml")


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


def get_combined_rss_feed(request):
    nr = create_nr_podcast({"url": "combined/", "name": "Nocne Radio (+ YouTube)"})
    ids = [y.get_filename() for y in models.Episode.objects.all() if y.is_visible()]

    for ep in ids:
        add_episode(nr, services.get_file_data(ep))

    for ep in get_radio_feed():
        add_episode(nr, ep)

    return HttpResponse(nr.rss_str(), content_type="text/xml")
