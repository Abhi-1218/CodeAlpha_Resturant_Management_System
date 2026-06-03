import os
import threading
import webbrowser

from django.contrib.staticfiles.management.commands.runserver import Command as StaticFilesRunserverCommand


class Command(StaticFilesRunserverCommand):
    help = "Starts the Django development server and opens the restaurant dashboard."

    def inner_run(self, *args, **options):
        if os.environ.get("RUN_MAIN") == "true" and not os.environ.get("RESTAURANT_DASHBOARD_OPENED"):
            os.environ["RESTAURANT_DASHBOARD_OPENED"] = "true"
            url = f"http://{self.addr}:{self.port}/"
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()

        super().inner_run(*args, **options)
