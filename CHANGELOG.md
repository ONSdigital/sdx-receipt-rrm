### Unreleased
  - Remove Cloudfoundry deployment files

### 2.18.2 2020-05-21
  - Add 60 second timeout to requests and add error logging
  - Updated packages

### 2.18.1 2019-11-08
  - Add python 3.8 to travis builds

### 2.18.0 2019-09-04
  - Updated sdc-rabbit to 1.7.0 to fix reconnection issues
  - Updated various other dependencies

### 2.17.0 2019-08-01
  - Reverted to default heartbeat

### 2.16.0 2019-06-20
  - Remove python 3.4 and 3.5 from travis builds
  - Add python 3.7 to travis builds
  - Update sdc-rabbit, tornado and pika to allow upgrade to python 3.7

### 2.15.2 2019-05-14
  - Fix bug where previous submissions field values were bound to log lines of current submission
  - Update packages with security issues

### 2.15.1 2019-03-14
  - Bound case_id , tx_id and user_id to logger

### 2.15.0 2019-01-22
  - Add userId to receipt

### 2.14.0 2018-11-13
  - Add startup log with version

### 2.13.0 2018-09-11
  - Remove all code relating to RRM service

### 2.12.0 2018-06-27
  - Remove second rabbit host

### 2.11.0 2018-03-06
  - Send receipts to RM based on the presence of a case_id field

### 2.10.0 2018-01-17
  - Add heartbeat interval to rabbit mq url

### 2.9.0 2017-11-21
  - Add Cloudfoundry deployment files
  - Remove sdx-common logging

### 2.8.0 2017-11-01
  - Add all service config to config file
  - Ensure tx_id is being passed in header
  - Change to use pytest to improve test output. Also improve code coverage stats

### 2.7.0 2017-10-16
  - Hardcode unchanging variables in settings.py to make configuration management simpler
  - Add more logging around receipt being sent to RRM

### 2.6.0 2017-10-02
  - Handle network errors using the ConnectionError exception class and requeing the message

### 2.5.0 2017-09-25
  - Removed SDX common clone in docker
  - Integrate with sdc-rabbit library
  - Pass tx_id=False to process method to not check if a tx_id is received

### 2.4.0 2017-09-11
  - Ensure integrity and version of library dependencies

### 2.3.0 2017-07-25
  - Change all instances of ADD to COPY in Dockerfile

### 2.2.0 2017-07-10
  - Timestamp all logs as UTC
  - Add common library logging
  - Route receipt 404 errors correctly
  - Add the service being called to `calling service` logging message
  - Add all environment variables to README
  - Add codacy badge
  - Correct license attribution
  - Add support for codecov to see unit test coverage
  - Update and pin version of sdx-common to 0.7.0

### 2.1.1 2017-03-22
  - Remove the Rabbit URL from logging message

### 2.1.0 2017-03-15
  - Log version number on startup
  - Align async consumer with sdx-receipt-ctp
  - Amend `stats_code` to 'status' in response_processor for SDX logging

### 2.0.0 2017-02-16
  - Add explicit ack/nack for messages based on processing success
  - Add support for encrypted queue messages from ``sdx-collect``
  - Add change log
  - Remove reject on max retries. Stops message being rejected if endpoint is down for prolonged period
  - Update logging to reduce noise and be more consistent, adding queue name to message
  - Add `PREFETCH=1` to rabbit config to address '104 Socket' errors
  - Update env var for queue name

### 1.0.0 2016-11-22
  - Initial release
