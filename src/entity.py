

from pydantic import BaseModel


# --------------------------------------------------
# Shared API Models
# --------------------------------------------------

class OpenAQMeta(BaseModel):
    name: str
    website: str
    page: int
    limit: int
    found: int | str | None = None


class DateTimePair(BaseModel):
    utc: str
    local: str


class Parameter(BaseModel):
    id: int
    name: str
    units: str
    displayName: str | None = None


class Coordinates(BaseModel):
    latitude: float | None = None
    longitude: float | None = None


# --------------------------------------------------
# Location Models (GET /v3/locations)
# --------------------------------------------------

class Country(BaseModel):
    id: int | None = None
    code: str
    name: str


class Owner(BaseModel):
    id: int
    name: str


class Provider(BaseModel):
    id: int
    name: str


class Instrument(BaseModel):
    id: int
    name: str


class Sensor(BaseModel):
    id: int
    name: str
    parameter: Parameter


class Attribution(BaseModel):
    name: str
    url: str | None = None


class License(BaseModel):
    id: int
    name: str
    attribution: Attribution
    dateFrom: str | None = None
    dateTo: str | None = None


class LocationRecord(BaseModel):
    id: int
    name: str | None = None
    locality: str | None = None
    timezone: str
    country: Country
    owner: Owner
    provider: Provider
    instruments: list[Instrument]
    sensors: list[Sensor]
    coordinates: Coordinates
    licenses: list[License] | None = None
    bounds: list[float]
    distance: float | None = None
    datetimeFirst: DateTimePair | None = None
    datetimeLast: DateTimePair | None = None
    isMobile: bool | None = None
    isMonitor: bool | None = None


# --------------------------------------------------
# Hourly Measurement Models (GET /v3/sensors/{id}/hours)
# --------------------------------------------------

class FlagInfo(BaseModel):
    hasFlags: bool | None = None


class Period(BaseModel):
    label: str | None = None
    interval: str | None = None
    datetimeFrom: DateTimePair
    datetimeTo: DateTimePair


class Summary(BaseModel):
    min: float | None = None
    max: float | None = None
    avg: float | None = None
    median: float | None = None
    sd: float | None = None
    q02: float | None = None
    q25: float | None = None
    q75: float | None = None
    q98: float | None = None


class Coverage(BaseModel):
    expectedCount: int | None = None
    observedCount: int | None = None
    percentComplete: float | None = None
    percentCoverage: float | None = None
    expectedInterval: str | None = None
    observedInterval: str | None = None
    datetimeFrom: DateTimePair | None = None
    datetimeTo: DateTimePair | None = None


class HourlyRecord(BaseModel):
    value: float | None = None        # TARGET VARIABLE: PM2.5 in µg/m³
    parameter: Parameter
    period: Period
    flagInfo: FlagInfo | None = None
    coordinates: Coordinates | None = None
    summary: Summary | None = None
    coverage: Coverage | None = None