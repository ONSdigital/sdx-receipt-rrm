### Unreleased
  

### 2.1.0 2017-03-15
  - Log version number on startup
  - Align async consumer with sdx-receipt-ctp
  - Add the service being called to `calling service` logging message

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
