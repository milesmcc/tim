#!/bin/bash

# Start Gunicorn processes
echo Launching Tim web server...
exec gunicorn tim.wsgi:application \
    --bind 0.0.0.0:8080 \
    --workers 3 \
    --timeout 100