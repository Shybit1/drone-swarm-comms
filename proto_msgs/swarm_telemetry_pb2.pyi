from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class NeighborStateEstimate(_message.Message):
    __slots__ = ["estimate_age_us", "estimate_confidence", "estimated_position", "estimated_velocity", "estimator_id", "neighbor_id"]
    ESTIMATED_POSITION_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_VELOCITY_FIELD_NUMBER: _ClassVar[int]
    ESTIMATE_AGE_US_FIELD_NUMBER: _ClassVar[int]
    ESTIMATE_CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    ESTIMATOR_ID_FIELD_NUMBER: _ClassVar[int]
    NEIGHBOR_ID_FIELD_NUMBER: _ClassVar[int]
    estimate_age_us: int
    estimate_confidence: float
    estimated_position: Vector3
    estimated_velocity: Vector3Vel
    estimator_id: int
    neighbor_id: int
    def __init__(self, estimator_id: _Optional[int] = ..., neighbor_id: _Optional[int] = ..., estimated_position: _Optional[_Union[Vector3, _Mapping]] = ..., estimated_velocity: _Optional[_Union[Vector3Vel, _Mapping]] = ..., estimate_age_us: _Optional[int] = ..., estimate_confidence: _Optional[float] = ...) -> None: ...

class SwarmTelemetry(_message.Message):
    __slots__ = ["battery_percent", "drone_id", "fire_detected", "fire_intensity", "fuel_distance_m", "link_quality", "payload_remaining", "position", "rssi_dbm", "state", "timestamp_us", "velocity"]
    class DroneState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    BATTERY_PERCENT_FIELD_NUMBER: _ClassVar[int]
    DRONE_ID_FIELD_NUMBER: _ClassVar[int]
    FIRE_DETECTED_FIELD_NUMBER: _ClassVar[int]
    FIRE_INTENSITY_FIELD_NUMBER: _ClassVar[int]
    FORMATION: SwarmTelemetry.DroneState
    FUEL_DISTANCE_M_FIELD_NUMBER: _ClassVar[int]
    IDLE: SwarmTelemetry.DroneState
    LINK_QUALITY_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_REMAINING_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    RETURN_TO_DOCK: SwarmTelemetry.DroneState
    RETURN_TO_LAUNCH: SwarmTelemetry.DroneState
    RSSI_DBM_FIELD_NUMBER: _ClassVar[int]
    SEARCH: SwarmTelemetry.DroneState
    STATE_FIELD_NUMBER: _ClassVar[int]
    SUPPRESS: SwarmTelemetry.DroneState
    TIMESTAMP_US_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    battery_percent: float
    drone_id: int
    fire_detected: bool
    fire_intensity: float
    fuel_distance_m: int
    link_quality: float
    payload_remaining: int
    position: Vector3
    rssi_dbm: int
    state: SwarmTelemetry.DroneState
    timestamp_us: int
    velocity: Vector3Vel
    def __init__(self, drone_id: _Optional[int] = ..., timestamp_us: _Optional[int] = ..., position: _Optional[_Union[Vector3, _Mapping]] = ..., velocity: _Optional[_Union[Vector3Vel, _Mapping]] = ..., battery_percent: _Optional[float] = ..., payload_remaining: _Optional[int] = ..., fuel_distance_m: _Optional[int] = ..., state: _Optional[_Union[SwarmTelemetry.DroneState, str]] = ..., fire_detected: bool = ..., fire_intensity: _Optional[float] = ..., rssi_dbm: _Optional[int] = ..., link_quality: _Optional[float] = ...) -> None: ...

class Vector3(_message.Message):
    __slots__ = ["x", "y", "z"]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class Vector3Vel(_message.Message):
    __slots__ = ["vx", "vy", "vz"]
    VX_FIELD_NUMBER: _ClassVar[int]
    VY_FIELD_NUMBER: _ClassVar[int]
    VZ_FIELD_NUMBER: _ClassVar[int]
    vx: float
    vy: float
    vz: float
    def __init__(self, vx: _Optional[float] = ..., vy: _Optional[float] = ..., vz: _Optional[float] = ...) -> None: ...
