#!/bin/sh
# GIT_ASKPASS helper.
#
# git calls this with the prompt text as $1, e.g.
#   Username for 'https://github.com':
#   Password for 'https://user@github.com':
#
# Credentials arrive via the environment so that the token never lands on
# disk and never enters .git/config or git's error output.
#
# Anything that is not a username prompt is treated as a password prompt:
# when the URL already carries a username, git only asks for the password
# and the wording may vary between versions.

case "$1" in
    Username*|username*) printf '%s' "${HACGB_GIT_USERNAME}" ;;
    *) printf '%s' "${HACGB_GIT_PASSWORD}" ;;
esac
