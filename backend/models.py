from dataclasses import dataclass


@dataclass
class NodeInfo:
    port: str
    address: int
    type_name: str
    serial: str
    channels: int
    node_id: str
