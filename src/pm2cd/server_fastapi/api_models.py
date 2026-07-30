from typing import Any, List, Union

from pydantic import BaseModel


class ResultResponse(BaseModel):
    result: Any = None


class IntResponse(BaseModel):
    result: int


class FloatResponse(BaseModel):
    result: float


class BoolResponse(BaseModel):
    result: bool


class StrResponse(BaseModel):
    result: str


class MoveRequest(BaseModel):
    motor: int
    pulse: int
    backlash: Union[str, bool] = True


class MoveRelativeRequest(BaseModel):
    motor: int
    pulse: int
    backlash: Union[str, bool] = True


class ScanRequest(BaseModel):
    motor: int
    direction: str


class ConstantSpeedScanRequest(BaseModel):
    motor: int
    direction: str


class JogRequest(BaseModel):
    motor: int
    direction: str


class HomeRequest(BaseModel):
    motor: int


class FindHomeRequest(BaseModel):
    motor: int


class StopRequest(BaseModel):
    motor: int


class EmergencyStopRequest(BaseModel):
    motor: int


class StatusRequest(BaseModel):
    motor: int


class IsBusyRequest(BaseModel):
    motor: int


class WaitStopRequest(BaseModel):
    motor: int
    timeout_sec: float = 30.0
    interval_sec: float = 0.1


class PositionRequest(BaseModel):
    motor: int


class SetPositionRequest(BaseModel):
    motor: int
    pulse: int


class SetSpeedRequest(BaseModel):
    motor: int
    speed: int


class HighSpeedRequest(BaseModel):
    motor: int


class SetHighSpeedRequest(BaseModel):
    motor: int
    speed: int


class MiddleSpeedRequest(BaseModel):
    motor: int


class SetMiddleSpeedRequest(BaseModel):
    motor: int
    speed: int


class LowSpeedRequest(BaseModel):
    motor: int


class SetLowSpeedRequest(BaseModel):
    motor: int
    speed: int


class SpeedModeRequest(BaseModel):
    motor: int


class SetSpeedModeRequest(BaseModel):
    motor: int
    mode: Union[int, str]


class RateNumberRequest(BaseModel):
    motor: int


class SetRateNumberRequest(BaseModel):
    motor: int
    number: int


class BacklashRequest(BaseModel):
    motor: int


class SetBacklashRequest(BaseModel):
    motor: int
    backlash: int


class LimitRequest(BaseModel):
    motor: int
    side: str


class SetLimitRequest(BaseModel):
    motor: int
    side: str
    pulse: int


class HoldRequest(BaseModel):
    motor: int


class SetHoldRequest(BaseModel):
    motor: int
    enabled: bool


class TtlOutputStartRequest(BaseModel):
    motor: int


class TtlOutputStopRequest(BaseModel):
    motor: int


class TtlStatusRequest(BaseModel):
    motor: int


class NumberToRateRequest(BaseModel):
    index: int


class RateToNumberRequest(BaseModel):
    rate: float

