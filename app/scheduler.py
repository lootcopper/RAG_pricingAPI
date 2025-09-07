import importlib
import inspect
import logging
import pkgutil

from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.interval import IntervalTrigger

import scrapers
from app.config import scraper_config
from app.db import (
    repository_model,
    repository_provider,
    repository_provider_model,
)
from app.db.session import SessionLocal
from scrapers.base import BaseProviderModelScraper, ProviderModelSpec


def discover_scrapers() -> list[type[BaseProviderModelScraper]]:
    """Dynamically discovers all scraper classes in the scrapers package."""
    discovered_scrapers = []
    package_path = scrapers.__path__
    package_name = scrapers.__name__

    for _, name, _ in pkgutil.iter_modules(package_path, prefix=f"{package_name}."):
        try:
            module = importlib.import_module(name)
            for _, member_obj in inspect.getmembers(module):
                if (
                    inspect.isclass(member_obj)
                    and issubclass(member_obj, BaseProviderModelScraper)
                    and member_obj is not BaseProviderModelScraper
                ):
                    logging.info(f"Discovered scraper: {member_obj.__name__}")
                    discovered_scrapers.append(member_obj)
        except Exception as e:
            logging.error(f"Failed to import or inspect module {name}: {e}")

    return discovered_scrapers


def run_job(scraper_class: type[BaseProviderModelScraper]):
    """The main job function that runs a single scraper and updates the database."""
    logging.info(f"--- Starting job for {scraper_class.__name__} ---")
    db = SessionLocal()
    try:
        scraper = scraper_class()
        scraped_data: list[ProviderModelSpec] = scraper.scrape()
        logging.info(
            f"Scraped {len(scraped_data)} model offerings from {scraper_class.__name__}."
        )

        for spec in scraped_data:
            provider = repository_provider.get_or_create_provider(
                db,
                name=spec.provider_name,
                website=spec.provider_website,
                api_key_name=spec.provider_api_key_name,
            )
            model = repository_model.get_or_create_model(
                db, model_name=spec.model_name
            )
            repository_provider_model.add_model_to_provider(
                db,
                provider_id=provider.id,
                model_id=model.id,
                api_model_name=spec.api_model_name,
                context_window=spec.context_window,
                max_output_tokens=spec.max_output_tokens,
                input_cost_per_mtok=spec.input_cost_per_mtok,
                output_cost_per_mtok=spec.output_cost_per_mtok,
                tokens_per_second=spec.tokens_per_second,
                modalities=spec.modalities,
                supports_tools=spec.supports_tools,
                discount_start_time_utc=spec.discount_start_time_utc,
                discount_end_time_utc=spec.discount_end_time_utc,
                input_discount_price=spec.input_discount_price,
                output_discount_price=spec.output_discount_price,
                cached_input_cost_per_mtok=spec.cached_input_cost_per_mtok,  # NEW FIELD
            )
        logging.info(f"Successfully processed data for {scraper_class.__name__}.")

    except Exception as e:
        logging.error(f"Job for {scraper_class.__name__} failed: {e}", exc_info=True)
    finally:
        db.close()
        logging.info(f"--- Finished job for {scraper_class.__name__} ---")


def schedule_jobs(scheduler: BaseScheduler):
    """Discovers scrapers and schedules them to run."""
    scrapers = discover_scrapers()

    logging.info(f"Scheduler interval set to {scraper_config.SCHEDULE_INTERVAL_MINS} minutes.")
    if scraper_config.RUN_ON_STARTUP:
        logging.info("Scheduling jobs to run on startup.")
    else:
        logging.info("Run on startup is disabled.")

    if not scrapers:
        logging.warning("No scrapers found. Scheduler will start but have no jobs.")

    for scraper_cls in scrapers:
        if scraper_config.RUN_ON_STARTUP:
            # Schedule to run once on startup
            scheduler.add_job(
                run_job,
                args=[scraper_cls],
                id=f"startup_job_{scraper_cls.__name__}",
                name=f"Startup scraper job for {scraper_cls.__name__}",
            )

        # Schedule to run at a regular interval
        scheduler.add_job(
            run_job,
            trigger=IntervalTrigger(minutes=scraper_config.SCHEDULE_INTERVAL_MINS),
            args=[scraper_cls],
            id=f"job_{scraper_cls.__name__}",
            name=f"Scraper job for {scraper_cls.__name__}",
        )
