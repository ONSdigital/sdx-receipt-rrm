build:
	git clone -b 0.7.0 https://github.com/ONSdigital/sdx-common.git
	pip install ./sdx-common
	pip3 install --require-hashes -r requirements.txt
	rm -rf sdx-common

test:
	pip3 install -r test_requirements.txt
	flake8 --exclude lib
	python3 -m unittest tests/*.py

start:
	./startup.sh

clean:
	rm -rf ./sdx-common
