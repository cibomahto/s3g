# s3g

S3g is an attempt at implementing the MakerBot serial protocol in python. The main goal is to control some plotter devices. If it proves useful, then certainly something else could be done with it.

## Usage

For now, just some unit tests:

    python s3g_test.py

Once it can pass these, then some comms handler, etc. It's only going to support a blocking interface.

## Reference

See the [RepRap Generation 3 (s3g) Protocol Specification](https://docs.google.com/a/makerbot.com/document/d/1oq-oEogcRxJ91ex4_cJLs8bXPmWoTKJRNPz9Amh0Hb4/edit#heading=h.054a1e7d67e9)
