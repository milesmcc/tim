#!/bin/bash

# Start queue worker processes
echo Launching Tim queue worker...
exec celery -A tim worker -E --loglevel=INFO --concurrency=3