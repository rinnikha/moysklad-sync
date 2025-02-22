import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
import atexit
import threading

scheduler = None
scheduler_lock = threading.Lock()

def start_scheduler(app):
    if not hasattr(app, 'scheduler'):
        app.scheduler = BackgroundScheduler(daemon=True)

    global scheduler
    with scheduler_lock:
        if scheduler and scheduler.running:
            return

        # Only start scheduler in main process, not reloader
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true' and os.environ.get('FLASK_DEBUG') == '1':
            return

        scheduler = BackgroundScheduler(daemon=True)
        scheduler.configure(timezone="UTC")

        def sync_job():
            with app.app_context():
                from app.sync.core import sync_orders
                sync_orders()

        scheduler.add_job(
            sync_job,
            'interval',
            hours=1,
            id='hourly_sync',
            replace_existing=True,
            max_instances=1
        )

        scheduler.start()
        atexit.register(shutdown_scheduler)

def shutdown_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None