#!/bin/sh
set -eu

api_url="${PIKATRAP_API_URL:-http://localhost:8000}"
sed "s|__PIKATRAP_API_URL__|${api_url}|g" /usr/share/nginx/html/lab.js > /tmp/lab.js
mv /tmp/lab.js /usr/share/nginx/html/lab.js

exec nginx -g "daemon off;"
