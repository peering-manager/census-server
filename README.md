# Peering Manager Census API

This repository contains the API server code that takes care of handling
Peering Manager census records.

Census records are sent by Peering Manager instances running a version of the
code greater or equal to 1.9.0, if the `CENSUS_REPORTING_ENABLED` setting of
those instances is set to `True`.

This server is in charge of storing census records in a database as well as
providing a way to read those records. It is able to send notifications when a
record is created or updated.

A census record is composed of:

* `deployment_id` a pseudorandom unique identifier which goal is to
  anonymously identify a single instance of Peering Manager
* `version` the Peering Manager code version run by the instance
* `python_version` the Python version used by the instance
* `country` the code of the country where the instance is probably located,
  the value is infered from the IP address (which is not stored)

Census reporting is performed by sending a POST request to the
`/api/v1/records/` endpoint with the following data:

```json
{
    "deployment_id": "DEPLOYMENT_ID",
    "version": "VERSION",
    "python_version": "PYTHON_VERSION"
}
```
