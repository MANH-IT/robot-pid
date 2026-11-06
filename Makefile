PORT ?= /dev/ttyUSB0
ESP ?= 192.168.4.1:8080

.PHONY: test sim monitor monitor-wifi wifi firmware upload clean

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

clean:
	rm -rf host/__pycache__ host/robot_host/__pycache__ host/tests/__pycache__
	rm -rf host/.pytest_cache firmware/.pio
