#!/bin/sh

# Sanitize the DEFAULT_BACKEND_URL by escaping special characters for JavaScript
sanitize_url() {
  # Replace backslashes, single quotes, and control characters
  printf '%s' "$1" | sed "s/\\\\/\\\\\\\\/g; s/'/\\\\'/g; s/\"/\\\\\"/g"
}

DEFAULT_BACKEND_URL_RAW="${DEFAULT_BACKEND_URL:-}"
SANITIZED_URL=$(sanitize_url "${DEFAULT_BACKEND_URL_RAW}")

if [ -n "$DEFAULT_BACKEND_URL_RAW" ]; then
  DEFAULT_BACKEND_VALUE="'${SANITIZED_URL}'"
else
  DEFAULT_BACKEND_VALUE="window.location.origin + '/clash-api'"
fi

# Generate config.js from environment variables
cat > /app/.output/public/config.js << EOF
window.__METACUBEXD_CONFIG__ = {
  defaultBackendURL: ${DEFAULT_BACKEND_VALUE},
}
EOF

# Start Node.js server
exec node /app/.output/server/index.mjs
