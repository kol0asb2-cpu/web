PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

.PHONY: help setup install run clean reset

help:
	@echo "Available commands:"
	@echo "  make setup   - create virtualenv and install dependencies"
	@echo "  make install - install dependencies into existing virtualenv"
	@echo "  make run     - run the judger"
	@echo "  make clean   - remove output files"
	@echo "  make reset   - remove virtualenv and output files"

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	mkdir -p output
	$(PY) src/run_judger.py

clean:
	rm -f output/judged_watchlist.csv
	rm -f output/judged_watchlist.md

reset: clean
	rm -rf $(VENV)