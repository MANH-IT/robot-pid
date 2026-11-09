PORT ?= /dev/ttyUSB0
ESP ?= 172.20.10.10:8080

.PHONY: test sim monitor monitor-wifi wifi firmware upload esp8266 esp8266-upload clean

test:
	cd host && python3 -m pytest -q

sim:
	cd host && python3 main.py --sim

monitor:
	cd host && python3 main.py --port $(PORT) --monitor

monitor-wifi:
	cd host && python3 main.py --tcp $(ESP) --monitor

wifi:
	cd host && python3 main.py --tcp $(ESP)

firmware:
	pio run -d firmware

upload:
	pio run -d firmware -t upload

esp8266:
	pio run -d esp8266

esp8266-upload:
	pio run -d esp8266 -t upload

clean:
	rm -rf host/__pycache__ host/robot_host/__pycache__ host/tests/__pycache__ tools/__pycache__
	rm -rf host/.pytest_cache host/.ruff_cache .pytest_cache .ruff_cache
	rm -rf host/*.egg-info host/build firmware/.pio esp8266/.pio
