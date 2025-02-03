import argparse
import json
import logging
import pprint
from dataclasses import dataclass
from typing import Iterable, Optional

import requests

logger = logging.getLogger(__name__)


#
# Example
# python3 notifiarr.py -e "System Backup" -k "${API_KEY}" -c 735481457153277994 -m "FFA500" -t "Backup Failed" -f "[{\"Reason\": \"Permissions error\"}, {\"Severity\": \"Critical\"}]" -a "https://notifiarr.com/images/logo/notifiarr.png" -z "Passthrough Integration"
# python3 notifiarr.py -e "System Backup" -k "${API_KEY}" -c 735481457153277994 -m "FFA500" -t "Backup Failed" -b "Critical permissions error" -a "https://notifiarr.com/images/logo/notifiarr.png" -z "Passthrough Integration"
#
@dataclass
class NotificationField:
    title: str
    text: str


def send_notification(
    api_key: str,
    channel_id: int,
    event: str,
    title: str,
    body: Optional[str] = None,
    fields: Optional[Iterable[NotificationField]] = None,
    inline_fields: Optional[Iterable[NotificationField]] = None,
    footer: str = "",
    avatar_url: str = "",
    thumbnail_url: str = "",
    color: str = "",
    ping_user_id: int = 0,
    ping_role_id: int = 0,
    dry_run=False,
):
    """Send a passthrough notification via Notifiarr.

    Args:
        api_key: API key for requests
        event: Notification type (e.g. "System Backup")
        channel_id: Valid Discord channel ID
        title: Text title of the message (e.g. "Backup Failed")
        body: If fields is not used, text body for message
        fields: If body is not used, valid list of fields [{title,text}, {title,text}] max 25 list items (not inline)
        inline_fields: If body is not used, valid list of fields [{title,text}, {title,text}] max 25 list items (inline)
        footer: Text footer of the message
        avatar_url: Valid url to image
        thumbnail_url: Valid url to image
        color: 6 digit HTML code for the color
        ping_user_id: Valid discord user ID
        ping_role_id: Valid discord role ID
        dry_run: Simply logs if true
    """
    if not body and fields is None and inline_fields is None:
        raise ValueError("Either body, fields, or inline_fields is required")

    combined_fields = []
    if fields is not None:
        combined_fields += [{"title": field.title, "text": field.text, "inline": False} for field in fields]
    if inline_fields is not None:
        combined_fields += [{"title": field.title, "text": field.text, "inline": True} for field in inline_fields]

    notifiarr_payload = {
        "notification": {"update": False, "name": event, "event": 0},
        "discord": {
            "color": color,
            "ping": {"pingUser": ping_user_id, "pingRole": ping_role_id},
            "images": {"thumbnail": thumbnail_url, "image": ""},
            "text": {
                "title": title,
                "icon": avatar_url,
                "content": "",
                "description": body,
                "fields": combined_fields,
                "footer": footer,
            },
            "ids": {"channel": channel_id},
        },
    }

    if dry_run:
        logger.info(f"Sending notification\n{pprint.pformat(notifiarr_payload)}")
        return

    resp = requests.post(
        f"https://notifiarr.com/api/v1/notification/passthrough/{api_key}",
        data=json.dumps(notifiarr_payload),
        headers={"Content-type": "application/json", "Accept": "text/plain"},
    )
    resp.raise_for_status()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Example: python notifiarr.py -e "System Backup" -k "${API_KEY}" -c 735481457153277994 -m "FFA500" -t "Backup Failed" -f "[{\\"Reason\\": \\"Permissions error\\"}, {\\"Severity\\": \\"Critical\\"}]" -g "[{\\"Reason\\": \\"Permissions error\\"}, {\\"Severity\\": \\"Critical\\"}]" -a "https://notifiarr.com/images/logo/notifiarr.png" -z "Passthrough Integration"'
    )
    parser.add_argument(
        "-e",
        "--event",
        dest="event",
        help="notification type (rclone for example)",
        type=str,
        required=True,
        metavar="",
    )
    parser.add_argument(
        "-k", "--api-key", dest="api_key", help="api key for requests", type=str, required=True, metavar=""
    )
    parser.add_argument(
        "-c", "--channel", dest="channel", help="valid discord channel id", type=int, required=True, metavar=""
    )
    parser.add_argument(
        "-t",
        "--title",
        dest="title",
        help="text title of message (rclone started for example)",
        type=str,
        required=True,
        metavar="",
    )
    parser.add_argument(
        "-b", "--body", dest="body", help="if fields is not used, text body for message", type=str, metavar=""
    )
    parser.add_argument(
        "-f",
        "--fields",
        dest="fields_not_inline",
        help="if body is not used, valid JSON list of fields [{title,text},{title,text}] max 25 list items (not inline)",
        type=str,
        metavar="",
    )
    parser.add_argument(
        "-g",
        "--inline",
        dest="fields_inline",
        help="if body is not used, valid JSON list of fields [{title,text},{title,text}] max 25 list items (inline)",
        type=str,
        metavar="",
    )
    parser.add_argument(
        "-z", "--footer", dest="footer", help="text footer of message", default="", type=str, metavar=""
    )
    parser.add_argument("-a", "--avatar", dest="avatar", help="valid url to image", default="", type=str, metavar="")
    parser.add_argument(
        "-i", "--thumbnail", dest="thumbnail", help="valid url to image", default="", type=str, metavar=""
    )
    parser.add_argument(
        "-m", "--color", dest="color", help="6 digit html code for the color", default="", type=str, metavar=""
    )
    parser.add_argument(
        "-u", "--ping-user", dest="ping_user", help="valid discord user id", default=0, type=int, metavar=""
    )
    parser.add_argument(
        "-r", "--ping-role", dest="ping_role", help="valid discord role id", default=0, type=int, metavar=""
    )
    args = parser.parse_args()

    if not args.api_key:
        raise Exception("ERROR: Must pass --api-key")

    if not args.body and not args.fields_not_inline and not args.fields_inline:
        raise Exception("ERROR: Either -b/--body or -f/--fields or -g/--inline is required")

    if args.fields_not_inline:
        fields = [NotificationField(k, v) for f in json.loads(args.fields_not_inline) for k, v in f.items()]
    else:
        fields = []

    if args.fields_inline:
        inline_fields = [NotificationField(k, v) for f in json.loads(args.fields_inline) for k, v in f.items()]
    else:
        inline_fields = []

    send_notification(
        api_key=args.api_key,
        event=args.event,
        channel_id=args.channel,
        title=args.title,
        body=args.body,
        fields=fields,
        inline_fields=inline_fields,
        footer=args.footer,
        avatar_url=args.avatar,
        thumbnail_url=args.thumbnail,
        color=args.color,
        ping_user_id=args.ping_user,
        ping_role_id=args.ping_role,
    )
