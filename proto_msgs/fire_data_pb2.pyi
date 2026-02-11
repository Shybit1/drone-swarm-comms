from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FireCell(_message.Message):
    __slots__ = ["fuel_density", "grid_x", "grid_y", "ignition_time_us", "intensity", "temperature_k"]
    FUEL_DENSITY_FIELD_NUMBER: _ClassVar[int]
    GRID_X_FIELD_NUMBER: _ClassVar[int]
    GRID_Y_FIELD_NUMBER: _ClassVar[int]
    IGNITION_TIME_US_FIELD_NUMBER: _ClassVar[int]
    INTENSITY_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_K_FIELD_NUMBER: _ClassVar[int]
    fuel_density: float
    grid_x: int
    grid_y: int
    ignition_time_us: int
    intensity: float
    temperature_k: float
    def __init__(self, grid_x: _Optional[int] = ..., grid_y: _Optional[int] = ..., intensity: _Optional[float] = ..., fuel_density: _Optional[float] = ..., temperature_k: _Optional[float] = ..., ignition_time_us: _Optional[int] = ...) -> None: ...

class FireDetection(_message.Message):
    __slots__ = ["detection_confidence", "detection_time_us", "drone_id", "intensity_estimate", "position_x", "position_y", "position_z"]
    DETECTION_CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    DETECTION_TIME_US_FIELD_NUMBER: _ClassVar[int]
    DRONE_ID_FIELD_NUMBER: _ClassVar[int]
    INTENSITY_ESTIMATE_FIELD_NUMBER: _ClassVar[int]
    POSITION_X_FIELD_NUMBER: _ClassVar[int]
    POSITION_Y_FIELD_NUMBER: _ClassVar[int]
    POSITION_Z_FIELD_NUMBER: _ClassVar[int]
    detection_confidence: float
    detection_time_us: int
    drone_id: int
    intensity_estimate: float
    position_x: float
    position_y: float
    position_z: float
    def __init__(self, drone_id: _Optional[int] = ..., detection_time_us: _Optional[int] = ..., detection_confidence: _Optional[float] = ..., position_x: _Optional[float] = ..., position_y: _Optional[float] = ..., position_z: _Optional[float] = ..., intensity_estimate: _Optional[float] = ...) -> None: ...

class FireMapState(_message.Message):
    __slots__ = ["cells", "grid_height", "grid_width", "max_intensity", "perimeter_cells", "timestamp_us", "total_burning_cells", "wind_direction_deg", "wind_speed_ms"]
    CELLS_FIELD_NUMBER: _ClassVar[int]
    GRID_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    GRID_WIDTH_FIELD_NUMBER: _ClassVar[int]
    MAX_INTENSITY_FIELD_NUMBER: _ClassVar[int]
    PERIMETER_CELLS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_US_FIELD_NUMBER: _ClassVar[int]
    TOTAL_BURNING_CELLS_FIELD_NUMBER: _ClassVar[int]
    WIND_DIRECTION_DEG_FIELD_NUMBER: _ClassVar[int]
    WIND_SPEED_MS_FIELD_NUMBER: _ClassVar[int]
    cells: _containers.RepeatedCompositeFieldContainer[FireCell]
    grid_height: int
    grid_width: int
    max_intensity: float
    perimeter_cells: int
    timestamp_us: int
    total_burning_cells: int
    wind_direction_deg: float
    wind_speed_ms: float
    def __init__(self, timestamp_us: _Optional[int] = ..., grid_width: _Optional[int] = ..., grid_height: _Optional[int] = ..., cells: _Optional[_Iterable[_Union[FireCell, _Mapping]]] = ..., wind_speed_ms: _Optional[float] = ..., wind_direction_deg: _Optional[float] = ..., total_burning_cells: _Optional[int] = ..., max_intensity: _Optional[float] = ..., perimeter_cells: _Optional[int] = ...) -> None: ...

class FireSuppression(_message.Message):
    __slots__ = ["drone_id", "payload_used", "suppression_strength", "suppression_time_us", "target_x", "target_y"]
    DRONE_ID_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_USED_FIELD_NUMBER: _ClassVar[int]
    SUPPRESSION_STRENGTH_FIELD_NUMBER: _ClassVar[int]
    SUPPRESSION_TIME_US_FIELD_NUMBER: _ClassVar[int]
    TARGET_X_FIELD_NUMBER: _ClassVar[int]
    TARGET_Y_FIELD_NUMBER: _ClassVar[int]
    drone_id: int
    payload_used: int
    suppression_strength: float
    suppression_time_us: int
    target_x: float
    target_y: float
    def __init__(self, drone_id: _Optional[int] = ..., suppression_time_us: _Optional[int] = ..., target_x: _Optional[float] = ..., target_y: _Optional[float] = ..., suppression_strength: _Optional[float] = ..., payload_used: _Optional[int] = ...) -> None: ...
