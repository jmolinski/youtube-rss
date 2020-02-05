import io
import xmlrpc
import xmlrpc.client

from datetime import datetime
from typing import Optional

from django.conf import settings

import requests

from PIL import Image
from platforma.platforma import models
from platforma.platforma.services import get_file_data


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


def image_to_byte_array(image, format='jpeq'):
    byte_stream = io.BytesIO()
    image.save(byte_stream, format=format)
    return byte_stream.getvalue()


def get_cropped_image_bytes(url):
    r = requests.get(url, stream=True)

    if not r.status_code == 200:
        return

    try:
        image = Image.open(io.BytesIO(r.content))
        w, h = image.size
        cropped = image.crop((0, 0, min(w, 846), min(h, 256)))
        return image_to_byte_array(cropped)
    except Exception as e:
        print("Failed to crop thumbnail")
        print("Error datails:", str(e), repr(e))
        return


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
        cropped_img = get_cropped_image_bytes(thumbnail_url)
        if cropped_img:
            try:
                img_data = client.wp.uploadFile(
                    0,
                    settings.NR_USERNAME,
                    settings.NR_PASSWD,
                    {
                        "name": episode.youtube_id + "_img.jpg",
                        "type": "image/jpeg",
                        "bits": xmlrpc.client.Binary(cropped_img),
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
            f"{date} \n{padded_description}Wpis utworzony automatycznie na podstawie audycji"
            f' na youtube: <a href="https://www.youtube.com/watch?v=PHHpI33Y7cA">link</a>\n\n'
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
        print("Submitted draft for", episode.youtube_id)
        episode.draft_posted = True
        episode.save()
    finally:
        episode.hidden = False
        episode.save()