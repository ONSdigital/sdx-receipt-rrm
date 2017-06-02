# sdx-receipt-rrm

[![Build Status](https://travis-ci.org/ONSdigital/sdx-receipt-rrm.svg?branch=develop)](https://travis-ci.org/ONSdigital/sdx-receipt-rrm) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/5c860d9fe90049e5ae570ac9c0d6a8e7)](https://www.codacy.com/app/ons-sdc/sdx-receipt-rrm?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ONSdigital/sdx-receipt-rrm&amp;utm_campaign=Badge_Grade)

``sdx-receipt-rrm`` is a component of the Office for National Statistics (ONS) Survey Data Exchange (SDX) product which sends receipts to RRM.

## Configuration

The main configuration options are listed below:

| Environment Variable            | Default                        | Description
|---------------------------------|--------------------------------|--------------
| RECEIPT_HOST                    | `http://sdx-mock-receipt:5000` | Host for rrm receipt service
| RECEIPT_PATH                    | `reportingunits`               | Path for rrm receipt service
| RECEIPT_USER                    | _none_                         | User for rrm receipt service
| RECEIPT_PASS                    | _none_                         | Password for rmm receipt service
| RABBIT_QUEUE                    | `rrm_receipt`                  | Incoming queue to read from
| RABBIT_EXCHANGE                 | `message`                      | RabbitMQ exchange to use
| RABBIT_QUARANTINE_QUEUE         | `rrm_receipt_quarantine`       | Rabbit quarantine queue
| SDX_RECEIPT_RRM_SECRET          | _none_                         | Key for decrypting messages from queue. Must be the same as used for ``sdx-collect``
| LOGGING_LEVEL                   | `DEBUG`                        | Logging sensitivity

### License

Copyright © 2016, Office for National Statistics (https://www.ons.gov.uk)

Released under MIT license, see [LICENSE](LICENSE) for details.