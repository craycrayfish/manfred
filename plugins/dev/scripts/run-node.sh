#!/bin/bash -l
# Runs node in a login shell so nvm/fnm/volta are sourced into PATH.
exec node "$@"
