#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
cd ..

# Load .env from the REPO ROOT — the same file `docker compose` reads and the
# one .env.example sits next to. Without this block, .env.example's "copy to
# .env and fill in" would be a lie: nothing else reads it.
#
# Anything already in the environment wins, which is the precedence python-dotenv
# and docker compose use, so `OPENROUTER_API_KEY=... ./run.sh` and an exported
# shell value both override the file.
if [ -f .env ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac                 # blank lines and comments
    case "$line" in 'export '*) line=${line#export } ;; esac  # "export KEY=v" is common
    key=${line%%=*}
    key=${key// /}                                            # tolerate "KEY = value"
    value=${line#*=}
    value=${value#"${value%%[! ]*}"}                          # ...and the space after the "="
    # Not a valid shell identifier; ${!key+x} below would abort under set -e.
    case "$key" in *[!A-Za-z0-9_]*) continue ;; esac
    case "$value" in                                          # strip one layer of quotes
      \"*\") value=${value#\"}; value=${value%\"} ;;
      \'*\') value=${value#\'}; value=${value%\'} ;;
    esac
    if [ -z "${!key+x}" ]; then                               # never clobber the real environment
      export "$key=$value"
    fi
  done < .env
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
