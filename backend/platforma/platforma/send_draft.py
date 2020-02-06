import io
import subprocess
import xmlrpc
import xmlrpc.client

from datetime import datetime
from typing import Optional

from django.conf import settings
from django.utils.text import slugify

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


def image_to_byte_array(image, format="jpeg"):
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


def upload_thumbnail(thumbnail_url, episode, client):
    if not thumbnail_url:
        print("No thumbnail data for episode", episode.youtube_id)
        return

    thumbnail_url = thumbnail_url.replace("hqdefault.jpg", "maxresdefault.jpg")
    cropped_img = get_cropped_image_bytes(thumbnail_url)
    if cropped_img:
        try:
            ret = client.wp.uploadFile(
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
            return ret
        except:
            print("Failed to upload thumbnail for", episode.youtube_id)


def upload_mp3_file_to_remote_server(episode, ep_data):
    date = f"{ep_data['day']:02d}_{ep_data['month']:02d}_{ep_data['year']:04}"
    slugified_title = slugify(ep_data["title"])

    remote_name = f"{slugified_title}-{date}-nr-yt-{episode.youtube_id}.mp3"
    episode.remote_filename = remote_name
    episode.save()

    try:
        ret = subprocess.call(
            [
                "scp",
                "-o",
                "StrictHostKeyChecking=no",
                f"/app/shared/media/{episode.get_filename()}",
                f"archiwum@nocneradio.pl:~/audycje/automat/{remote_name}",
            ],
            shell=False,
        )
        if ret != 0:
            raise ValueError(
                f"Error: scp returncode={ret} for episode {episode.get_filename()}"
            )
        return ret
    except:
        print("Error uploading file", episode.get_filename(), "to remote server")
        raise


def prepare_wordpress_post_content(episode, ep_data, img_data):
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
        f' na youtube: <a href="https://www.youtube.com/watch?v={episode.youtube_id}">link</a>\n\n'
        f"<!--ID###{episode.youtube_id} nr-yt==v0.0.1 {current_time}###-->\n"
    )
    content = {
        "post_type": "post",
        "post_title": original_title,
        # "post_excerpt": "test_excerpt",
        "post_content": description,
        "post_format": "standard",
        "comment_status": "open",
        "custom_fields": [
            {
                "key": "enclosure",
                "value": f"https://nocneradio.xyz/feeds/media/{episode.youtube_id}.mp3\n\naudio/mpeg",
            },
        ],
    }
    if img_data and "attachment_id" in img_data:
        content["post_thumbnail"] = int(img_data["attachment_id"])

    return content


def send_new_post_to_wordpress(episode, client, ep_data, img_data):
    try:
        content = prepare_wordpress_post_content(episode, ep_data, img_data)
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


def send_draft(episode: models.Episode):
    print("Submitting draft", episode.youtube_id)
    if episode.hidden or episode.draft_posted:
        print("Aborting sending draft for", episode.youtube_id)

    episode.hidden = True
    episode.save()

    client = xmlrpc.client.ServerProxy("http://nocneradio.pl/xmlrpc.php")
    ep_data = get_file_data(episode.get_filename())

    try:
        img_data: Optional[dict] = upload_thumbnail(
            ep_data["thumbnail"], episode, client
        )
        upload_mp3_file_to_remote_server(episode, ep_data)
        send_new_post_to_wordpress(episode, client, ep_data, img_data)
    except Exception as e:
        print("Problem submitting draft post for", episode.youtube_id)
        print("Error datails:", str(e), repr(e))
    finally:
        episode.hidden = False
        episode.save()
