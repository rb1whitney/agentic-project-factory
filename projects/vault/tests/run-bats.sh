#! /usr/bin/env bash

# Source setup-bats to install and export PATH
source ./tests/setup-bats.sh

# Run the tests
find ./tests -name "*.bats" -exec bats {} \;