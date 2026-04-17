#!/bin/bash
# Shadow SVN v3.1 - Engine Entrypoint
export LANG=C.UTF-8
export HOME=/tmp

echo "🛡️ Shadow SVN Engine Starting..."

# Control Panel (Flask + APScheduler handles all sync tasks)
exec gunicorn -w 1 -b 0.0.0.0:80 control_panel:app
