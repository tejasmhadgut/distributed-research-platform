import asyncio
from apscheduler.schedulers.blocking import BlockingScheduler
from app.scheduler.jobs import (
    run_daily_price_update,
    run_weekly_filing_refresh,
    run_weekly_embed_refresh,
)

scheduler = BlockingScheduler()


def main():
    scheduler.add_job(run_daily_price_update, "interval", days=1, id="daily_price_update")
    scheduler.add_job(run_weekly_filing_refresh, "interval", weeks=1, id="weekly_filing_refresh")
    scheduler.add_job(run_weekly_embed_refresh, "interval", weeks=1, id="weekly_embed_refresh")

    print("[scheduler] starting — jobs registered:")
    for job in scheduler.get_jobs():
        print(f"  {job.id}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[scheduler] shutting down")


if __name__ == "__main__":
    main()
