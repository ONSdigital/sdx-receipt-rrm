# sdx-receipt-rrm

[![Build Status](https://travis-ci.org/ONSdigital/sdx-receipt-rrm.svg?branch=develop)](https://travis-ci.org/ONSdigital/sdx-receipt-rrm) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/5c860d9fe90049e5ae570ac9c0d6a8e7)](https://www.codacy.com/app/ons-sdc/sdx-receipt-rrm?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ONSdigital/sdx-receipt-rrm&amp;utm_campaign=Badge_Grade) [![codecov](https://codecov.io/gh/ONSdigital/sdx-receipt-rrm/branch/develop/graph/badge.svg)](https://codecov.io/gh/ONSdigital/sdx-receipt-rrm)

``sdx-receipt-rrm`` is a component of the Office for National Statistics (ONS) Survey Data Exchange (SDX) product which sends receipts to RRM.

## Installation
This application presently installs required packages from requirements files:
- `requirements.txt`: packages for the application, with hashes for all packages: see https://pypi.org/project/hashin/
- `test-requirements.txt`: packages for testing and linting

It's also best to use `pyenv` and `pyenv-virtualenv`, to build in a virtual environment with the currently recommended version of Python.  To install these, see:
- https://github.com/pyenv/pyenv
- https://github.com/pyenv/pyenv-virtualenv
- (Note that the homebrew version of `pyenv` is easiest to install, but can lag behind the latest release of Python.)

### Getting started
Once your virtual environment is set, install the requirements:
```shell
$ make build
```

To test, first run `make build` as above, then run:
```shell
$ make test
```

It's also possible to install within a container using docker. From the sdx-receipt-rrm directory:
```shell
$ docker build -t sdx-receipt-rrm .
```

## Usage

Start sdx-receipt-rrm service using the following command:
```shell
$ make start
```

## Configuration

The main configuration options are listed below:

| Environment Variable            | Default                        | Description
|---------------------------------|--------------------------------|--------------
| RABBIT_QUEUE                    | `rrm_receipt`                  | Incoming queue to read from
| RABBIT_EXCHANGE                 | `message`                      | RabbitMQ exchange to use
| RABBIT_QUARANTINE_QUEUE         | `rrm_receipt_quarantine`       | Rabbit quarantine queue
| SDX_RECEIPT_RRM_SECRET          | _none_                         | Key for decrypting messages from queue. Must be the same as used for ``sdx-collect``
| LOGGING_LEVEL                   | `DEBUG`                        | Logging sensitivity

### License

Copyright (c) 2016 Crown Copyright (Office for National Statistics)

Released under MIT license, see [LICENSE](LICENSE) for details.

