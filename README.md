# h2pcontrol SDK

This kit provides tools to develop h2pcontrol clients and servers. 

## Requirements
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
uv add "h2pcontrol-sdk @ git+https://github.com/torbenfreise/h2pcontrol-sdk@0.2.5"  
```

## Usage
The SDK consists of two main components: the Client and Server implementations.
### h2pcontrol Server
The h2pcontrol server is an abc ([abstract base class](https://docs.python.org/3/library/abc.html))
that implements the shared functionality of all h2pcontrol services. It handles: 
 - Instantiating the gRPC server
 - Registering with as well as streaming logs and reporting health to the h2pcontrol manager

#### Configuration
The server can be configured with a `config.toml` file or environment variables.
An example configuration could be:
```toml
[manager]
address = "127.0.0.1:50051" # The address of the h2pcontrol manager
retry_interval_s = 5 # how often to attempt to (re)connect to the manager

[service]
name = "greeter" # A unique name for this service
description = "Greeter service" # a short description of the service and its purpose
address = "0.0.0.0:50055" # the address this service listens on and reports to the manager
```
The corresponding environment variables are defined as `<section>__<key>` and should be in all caps.
For example, defining `MANAGER__ADDRESS` overrides the manager address.


#### Implementation
Service implementations should inherit from `Server` along with the respective Servicer, and implement the `healthy` abstract method,
along with the methods inherited from the grpc service stub.
```python
from h2pcontrol.sdk.server import Server
from h2pcontrol.example.v1.example_pb2_grpc  import MyServiceServicer

class MyService(Server, MyServiceServicer):
    def healthy(self) -> bool:
        return True

    # implement gRPC service methods here


```
The `H2PServer` class defines `start`, which attempts to start the server and connect to the manager in parallel.
If the manager is unavailable, a warning log will be emitted and connection will be retried every `retry_interval_s`.


For a complete service implementation using this sdk, see the [h2pcontrol server template.](https://github.com/torbenfreise/h2pcontrol-server-template)


### Client
`Client` connects to the h2pcontrol manager and resolves named services to ready-to-use gRPC stubs.
Use it to connect to and manage h2pcontrol services:

```python
from h2pcontrol.sdk.client import Client, ServiceNotFoundError
from h2pcontrol.example.v1.example_pb2_grpc import ExampleServiceStub

async with Client("127.0.0.1:50051") as client:
    stub = await client.service("example", ExampleServiceStub)
    response = await stub.SayHello(...)
```

`service()` raises `ServiceNotFoundError` if the requested service is not registered with the manager.
