from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ConfigCommand(_message.Message):
    __slots__ = ["key", "value"]
    class ConfigKey(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    BATTERY_MIN_PERCENT: ConfigCommand.ConfigKey
    DETM_ETA0: ConfigCommand.ConfigKey
    DETM_LAMBDA: ConfigCommand.ConfigKey
    ENERGY_DRAIN_RATE: ConfigCommand.ConfigKey
    KEY_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_MAX: ConfigCommand.ConfigKey
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: ConfigCommand.ConfigKey
    value: float
    def __init__(self, key: _Optional[_Union[ConfigCommand.ConfigKey, str]] = ..., value: _Optional[float] = ...) -> None: ...

class DroneCommand(_message.Message):
    __slots__ = ["command_id", "command_type", "issued_time_us", "target_drone_id"]
    class CommandType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_TYPE_FIELD_NUMBER: _ClassVar[int]
    GOTO_POSITION: DroneCommand.CommandType
    HOLD: DroneCommand.CommandType
    ISSUED_TIME_US_FIELD_NUMBER: _ClassVar[int]
    LAND: DroneCommand.CommandType
    NOP: DroneCommand.CommandType
    RESUME: DroneCommand.CommandType
    RETURN_TO_DOCK: DroneCommand.CommandType
    RETURN_TO_LAUNCH: DroneCommand.CommandType
    SET_BATTERY_OVERRIDE: DroneCommand.CommandType
    SUPPRESS_FIRE: DroneCommand.CommandType
    TAKEOFF: DroneCommand.CommandType
    TARGET_DRONE_ID_FIELD_NUMBER: _ClassVar[int]
    command_id: int
    command_type: DroneCommand.CommandType
    issued_time_us: int
    target_drone_id: int
    def __init__(self, target_drone_id: _Optional[int] = ..., command_id: _Optional[int] = ..., issued_time_us: _Optional[int] = ..., command_type: _Optional[_Union[DroneCommand.CommandType, str]] = ...) -> None: ...

class GotoCommand(_message.Message):
    __slots__ = ["max_speed", "relative", "target_x", "target_y", "target_z"]
    MAX_SPEED_FIELD_NUMBER: _ClassVar[int]
    RELATIVE_FIELD_NUMBER: _ClassVar[int]
    TARGET_X_FIELD_NUMBER: _ClassVar[int]
    TARGET_Y_FIELD_NUMBER: _ClassVar[int]
    TARGET_Z_FIELD_NUMBER: _ClassVar[int]
    max_speed: float
    relative: bool
    target_x: float
    target_y: float
    target_z: float
    def __init__(self, target_x: _Optional[float] = ..., target_y: _Optional[float] = ..., target_z: _Optional[float] = ..., max_speed: _Optional[float] = ..., relative: bool = ...) -> None: ...

class SuppressionCommand(_message.Message):
    __slots__ = ["suppression_strength", "target_x", "target_y", "target_z"]
    SUPPRESSION_STRENGTH_FIELD_NUMBER: _ClassVar[int]
    TARGET_X_FIELD_NUMBER: _ClassVar[int]
    TARGET_Y_FIELD_NUMBER: _ClassVar[int]
    TARGET_Z_FIELD_NUMBER: _ClassVar[int]
    suppression_strength: float
    target_x: float
    target_y: float
    target_z: float
    def __init__(self, target_x: _Optional[float] = ..., target_y: _Optional[float] = ..., target_z: _Optional[float] = ..., suppression_strength: _Optional[float] = ...) -> None: ...
