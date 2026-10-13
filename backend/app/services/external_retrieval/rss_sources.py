"""Publisher-documented RSS feeds approved for Trend Radar retrieval.

The URLs below are copied from the publishers' own RSS directories. Additions
must be reviewed against the publisher directory and terms before use.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RSSFeedSource:
    feed_id: str
    publisher: str
    category: str
    url: str
    directory_url: str
    allowed_article_hosts: tuple[str, ...]


THANH_NIEN_RSS_DIRECTORY = "https://thanhnien.vn/rss.html"

TREND_RADAR_RSS_FEEDS = (
    RSSFeedSource(
        feed_id="thanhnien-consumer-smart",
        publisher="Báo Thanh Niên",
        category="Tiêu dùng thông minh",
        url="https://thanhnien.vn/rss/tieu-dung-thong-minh.rss",
        directory_url=THANH_NIEN_RSS_DIRECTORY,
        allowed_article_hosts=("thanhnien.vn",),
    ),
    RSSFeedSource(
        feed_id="thanhnien-food",
        publisher="Báo Thanh Niên",
        category="Ẩm thực",
        url="https://thanhnien.vn/rss/doi-song/am-thuc.rss",
        directory_url=THANH_NIEN_RSS_DIRECTORY,
        allowed_article_hosts=("thanhnien.vn",),
    ),
)

RSS_FEEDS_BY_URL = {source.url: source for source in TREND_RADAR_RSS_FEEDS}
RSS_FEEDS_BY_ID = {source.feed_id: source for source in TREND_RADAR_RSS_FEEDS}
