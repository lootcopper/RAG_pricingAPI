import os


class ScraperConfig:
    """Configuration for the scraper scheduler."""

    SCHEDULE_INTERVAL_MINS: int = int(os.getenv("SCHEDULE_INTERVAL_MINS", "1440"))

    RUN_ON_STARTUP: bool = os.getenv("RUN_ON_STARTUP", "true").lower() in (
        "true",
        "1",
        "t",
    )

    TIMEZONE: str = os.getenv("TIMEZONE", "UTC")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()


scraper_config = ScraperConfig()
