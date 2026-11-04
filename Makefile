PORT ?= /dev/ttyUSB0

.PHONY: test sim monitor firmware upload clean

test:
	cd host && python3 -m pytest -q

sim:
	cd host && python3 main.py --sim

monitor:
	cd host && python3 main.py --port $(PORT) --monitor

firmware:
	pio run -d firmware

upload:
	pio run -d firmware -t upload

clean:
	rm -rf host/__pycache__ host/robot_host/__pycache__ host/tests/__pycache__
	rm -rf host/.pytest_cache firmware/.pio
