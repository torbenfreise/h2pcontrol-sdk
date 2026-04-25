# h2pcontrol SDK

This kit provides tools to develop h2pcontrol clients and servers. 


## Installation
```bash
uv add "h2pcontrol-sdk @ git+https://github.com/torbenfreise/h2pcontrol-sdk@0.1.0"  
```

## Usage
The SDK consists of two main components: the Client and Server implementations.
### h2pcontrol Server
The h2pcontrol server is an abc ([abstract base class](https://docs.python.org/3/library/abc.html))
that implements the shared functionality of all h2pcontrol services. It handles: 
 - Instantiating the gRPC server
 - Registering with and reporting health to the h2pcontrol manager

#### Configuration
The server can be configured with a `config.toml` file or environment variables.
An example configuration could be:
```toml
[manager]
address = "127.0.0.1:50051" # The address of the h2pcontrol manager
heartbeat_interval_s = 5 # how often to ping the manager. also used within the retry mechanism 
                         # if the manager is unavailable
[service]
name = "greeter" # A unique name for this service
description = "Greeter service" # a short description of the service and its purpose
host = "0.0.0.0" # the address the gRPC server binds to
port = 50055 # the port the gRPC server binds to
```
The corresponding environment variables are defined as `<section>__<key>` and should be in all caps.
For example, defining `MANAGER__ADDRESS` overrides the manager address.


#### Implementation
Service implementations should inherit from `H2PServer` along with the respective Servicer, and implement the `healthy` abstract method,
along with the methods inherited from the grpc service stub.
```python
from h2pcontrol.sdk import H2PServer
from h2pcontrol.example.v1.example_pb2_grpc  import MyServiceServicer

class MyService(H2PServer, MyServiceServicer):
    def healthy(self) -> bool:
        return True

    # implement gRPC service methods here


```
The `H2PServer` class defines `start`, which attempts to start the server and connect to the manager in parallel.
If the manager is unavailable, a warning log will be emitted and connection will be retried every `heartbeat_interval_s`.


For a complete service implementation using this sdk, see the [h2pcontrol server template.](https://github.com/torbenfreise/h2pcontrol-server-template)


### Client
`H2PClient` connects to the h2pcontrol manager and resolves named services to ready-to-use gRPC stubs.
Use it to connect to and manage h2pcontrol services:

```python
from h2pcontrol.sdk import H2PClient, DeviceNotFoundError
from h2pcontrol.example.v1.example_pb2_grpc import ExampleServiceStub

async with H2PClient("127.0.0.1:50051") as client:
    stub = await client.service("example", ExampleServiceStub)
    response = await stub.SayHello(...)
```

`service()` raises `ServiceNotFoundError` if the requested service is not registered with the manager.


## Development / Contributing
### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
uv sync
```

### Format and linting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

Format code:

```bash
uv run ruff format src/
```

Check for lint issues:

```bash
uv run ruff check src/
```

Check for type issues:

```bash
 uv run pyright src/          
```


These checks also run automatically on every pull request and pushes to main via
the [GitHub Actions workflow](.github/workflows/lint.yml)

## Proto dependencies

Generated code is pulled from the [Buf Schema Registry](https://buf.build/beyer-labs/h2pcontrol) via the
`buf.build/gen/python` index configured in `pyproject.toml`. To update to the latest proto versions:

```bash
uv sync --upgrade
```