#!/bin/bash

# Start Gunicorn processes
echo Launching Tim beat worker...
exec celery -A tim beat --pidfile /tmp/celerybeat.pid -s /tmp/celerybeat-schedule