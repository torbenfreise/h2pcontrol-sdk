# Attribution

`src/h2pcontrol/sdk/client/_client.py` is derived from the `H2PControl` class written by Tijmen H.
Hilgenkamp, in https://github.com/BeyerLabVU/h2pcontrol_python at commit
`6fbe7d79d0c48af1a53847220f85315db4927902` (2025-06-06). 

Everything else in this repository is the work of the commit author.

## Seeing the diff

```sh
git clone https://github.com/BeyerLabVU/h2pcontrol_python /tmp/v1-python
git -C /tmp/v1-python checkout 6fbe7d7

diff -u /tmp/v1-python/src/h2pcontrol/h2pcontrol_connector.py src/h2pcontrol/sdk/client/_client.py
```
