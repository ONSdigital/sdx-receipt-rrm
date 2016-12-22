build:
	pip install -r requirements.txt

test:
	flake8 --exclude lib
	python3 -m unittest tests/*.py