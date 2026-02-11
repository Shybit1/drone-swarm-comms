from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DroneMetrics(_message.Message):
    __slots__ = ["average_neighbor_distance", "average_rssi_dbm", "battery_level", "drone_id", "fires_detected", "fires_suppressed", "formation_conflicts", "message_loss_count", "messages_received", "messages_sent", "time_in_rtl_us", "time_in_search_us", "time_in_suppress_us", "timestamp_us", "total_distance_m", "total_energy_used", "total_suppression_strength"]
    AVERAGE_NEIGHBOR_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_RSSI_DBM_FIELD_NUMBER: _ClassVar[int]
    BATTERY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    DRONE_ID_FIELD_NUMBER: _ClassVar[int]
    FIRES_DETECTED_FIELD_NUMBER: _ClassVar[int]
    FIRES_SUPPRESSED_FIELD_NUMBER: _ClassVar[int]
    FORMATION_CONFLICTS_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_RECEIVED_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_SENT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_LOSS_COUNT_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_US_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_RTL_US_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_SEARCH_US_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_SUPPRESS_US_FIELD_NUMBER: _ClassVar[int]
    TOTAL_DISTANCE_M_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ENERGY_USED_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SUPPRESSION_STRENGTH_FIELD_NUMBER: _ClassVar[int]
    average_neighbor_distance: float
    average_rssi_dbm: float
    battery_level: int
    drone_id: int
    fires_detected: int
    fires_suppressed: int
    formation_conflicts: int
    message_loss_count: int
    messages_received: int
    messages_sent: int
    time_in_rtl_us: int
    time_in_search_us: int
    time_in_suppress_us: int
    timestamp_us: int
    total_distance_m: float
    total_energy_used: float
    total_suppression_strength: float
    def __init__(self, drone_id: _Optional[int] = ..., timestamp_us: _Optional[int] = ..., total_distance_m: _Optional[float] = ..., total_energy_used: _Optional[float] = ..., battery_level: _Optional[int] = ..., messages_sent: _Optional[int] = ..., messages_received: _Optional[int] = ..., message_loss_count: _Optional[int] = ..., average_rssi_dbm: _Optional[float] = ..., fires_detected: _Optional[int] = ..., fires_suppressed: _Optional[int] = ..., total_suppression_strength: _Optional[float] = ..., formation_conflicts: _Optional[int] = ..., average_neighbor_distance: _Optional[float] = ..., time_in_search_us: _Optional[int] = ..., time_in_suppress_us: _Optional[int] = ..., time_in_rtl_us: _Optional[int] = ...) -> None: ...

class LatencyRecord(_message.Message):
    __slots__ = ["latency_us", "message_recv_time_us", "message_send_time_us", "receiver_id", "rssi_at_receipt_dbm", "sender_id"]
    LATENCY_US_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_RECV_TIME_US_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_SEND_TIME_US_FIELD_NUMBER: _ClassVar[int]
    RECEIVER_ID_FIELD_NUMBER: _ClassVar[int]
    RSSI_AT_RECEIPT_DBM_FIELD_NUMBER: _ClassVar[int]
    SENDER_ID_FIELD_NUMBER: _ClassVar[int]
    latency_us: int
    message_recv_time_us: int
    message_send_time_us: int
    receiver_id: int
    rssi_at_receipt_dbm: float
    sender_id: int
    def __init__(self, sender_id: _Optional[int] = ..., receiver_id: _Optional[int] = ..., message_send_time_us: _Optional[int] = ..., message_recv_time_us: _Optional[int] = ..., latency_us: _Optional[int] = ..., rssi_at_receipt_dbm: _Optional[float] = ...) -> None: ...

class SwarmMetrics(_message.Message):
    __slots__ = ["active_drones", "average_battery_percent", "average_formation_error", "average_message_interval_ms", "drone_metrics", "drones_critical_battery", "fire_coverage_percent", "formation_breaks", "landed_drones", "network_utilization_percent", "timestamp_us", "total_burning_cells", "total_messages", "total_suppressed_cells"]
    ACTIVE_DRONES_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_BATTERY_PERCENT_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_FORMATION_ERROR_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_MESSAGE_INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    DRONES_CRITICAL_BATTERY_FIELD_NUMBER: _ClassVar[int]
    DRONE_METRICS_FIELD_NUMBER: _ClassVar[int]
    FIRE_COVERAGE_PERCENT_FIELD_NUMBER: _ClassVar[int]
    FORMATION_BREAKS_FIELD_NUMBER: _ClassVar[int]
    LANDED_DRONES_FIELD_NUMBER: _ClassVar[int]
    NETWORK_UTILIZATION_PERCENT_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_US_FIELD_NUMBER: _ClassVar[int]
    TOTAL_BURNING_CELLS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_MESSAGES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SUPPRESSED_CELLS_FIELD_NUMBER: _ClassVar[int]
    active_drones: int
    average_battery_percent: float
    average_formation_error: float
    average_message_interval_ms: float
    drone_metrics: _containers.RepeatedCompositeFieldContainer[DroneMetrics]
    drones_critical_battery: int
    fire_coverage_percent: float
    formation_breaks: int
    landed_drones: int
    network_utilization_percent: float
    timestamp_us: int
    total_burning_cells: int
    total_messages: int
    total_suppressed_cells: int
    def __init__(self, timestamp_us: _Optional[int] = ..., active_drones: _Optional[int] = ..., landed_drones: _Optional[int] = ..., total_burning_cells: _Optional[int] = ..., total_suppressed_cells: _Optional[int] = ..., fire_coverage_percent: _Optional[float] = ..., total_messages: _Optional[int] = ..., average_message_interval_ms: _Optional[float] = ..., network_utilization_percent: _Optional[float] = ..., average_battery_percent: _Optional[float] = ..., drones_critical_battery: _Optional[int] = ..., average_formation_error: _Optional[float] = ..., formation_breaks: _Optional[int] = ..., drone_metrics: _Optional[_Iterable[_Union[DroneMetrics, _Mapping]]] = ...) -> None: ...
