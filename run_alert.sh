#!/bin/bash
# Portfolio alert runner - works locally and in GitHub Actions
cd "$(dirname "$0")"
python alert_runner.py
