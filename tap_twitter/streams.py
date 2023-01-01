"""Stream type classes for tap-twitter."""

from pathlib import Path
from typing import Any, Dict, List, Iterable

import requests

from tap_twitter.client import TwitterStream


SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class TweetsStream(TwitterStream):
    """Define custom stream."""
    name = "tweets"
    path = "/tweets/search/recent"
    primary_keys = ["id"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "tweets.schema.json"
    max_results = 100
    tweet_fields: List[str] = [
        "id",
        "text",
        "attachments",
        "author_id",
        "context_annotations",
        "conversation_id",
        "created_at",
        "entities",
        "geo",
        "in_reply_to_user_id",
        "lang",
        "possibly_sensitive",
        "public_metrics",
        "referenced_tweets",
        "reply_settings",
        "source",
        "withheld",
    ]
    user_fields: List[str] = [
        "id",
        "name",
        "username",
        "public_metrics",
    ]
    media_fields: List[str] = [
        "duration_ms",
        "height",
        "media_key",
        "preview_image_url",
        "type",
        "url",
        "width",
        "public_metrics",
        "non_public_metrics",
        "organic_metrics",
        "promoted_metrics",
        "alt_text",
        # "variants",
    ]
    expansions: List[str] = ["author_id","attachments.media_keys"]

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        record = response.json()
        if "includes" in record.keys():
            if "users" in record["includes"]:
                users_lookup = {user["id"]: user for user in record["includes"]["users"]}
            if "media" in record["includes"]:
                media_lookup = {media["media_key"]: media for media in record["includes"]["media"]}
        else:
            users_lookup = None
            media_lookup = None
        for i, tweet in enumerate(record.get("data", [])):
            if users_lookup:
                tweet["expansion__author_id"] = users_lookup[tweet["author_id"]]
            else:
                tweet["expansion__author_id"] = None
            if media_lookup and "attachments" in tweet and "media_keys" in tweet["attachments"]:
                tweet["media"] = [value for key, value in media_lookup.items() if key in tweet["attachments"]["media_keys"]]
            else:
                tweet["media"] = None
            yield tweet

    def make_query(self) -> str:
        user_ids = self.config.get("user_ids")
        url_patterns = self.config.get("url_patterns")
        from_filter = " OR ".join([f"from:{user_id}" for user_id in user_ids])

        if url_patterns:
            url_filter = " OR ".join([f"url:{url_pattern}" for url_pattern in url_patterns])
            query_elements = [from_filter, url_filter]
        else:
            query_elements = [from_filter]

        return " OR ".join(query_elements)

    def get_additional_url_params(self):
        return {
            "max_results": self.max_results,
            "query": self.make_query(),
            "tweet.fields": ",".join(self.tweet_fields),
            "expansions": ",".join(self.expansions),
            "user.fields": ",".join(self.user_fields),
            "media.fields": ",".join(self.media_fields),
        }


class UsersStream(TwitterStream):
    """Define custom stream."""
    name = "users"
    path = "/users"
    primary_keys = ["id"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "users.schema.json"
    user_fields: List[str] = [
        "id",
        "name",
        "username",
        "created_at",
        "description",
        "entities",
        "location",
        "pinned_tweet_id",
        "profile_image_url",
        "protected",
        "public_metrics",
        "url",
        "verified",
        "withheld",
    ]

    def get_additional_url_params(self):
        return {
            "ids": ",".join(self.config.get("user_ids")),
            "user.fields": ",".join(self.user_fields)
        }
