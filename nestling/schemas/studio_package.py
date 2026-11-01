"""StudioPackage: one photo studio's package as listed on its own page (Capture; also the future Partner API schema).

Every value is "as listed on the studio's site" on `checked_on`, from `source_url`.
A missing value stays None and is shown as "Not listed — ask the studio"; it is never guessed.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

NOT_LISTED = "Not listed — ask the studio"
ShootType = Literal["maternity", "baby_shower", "newborn", "casting"]


class Extra(BaseModel):
    name: str
    price_inr: int | None = None


class Album(BaseModel):
    offered: bool | None = None
    price_inr: int | None = None  # None with offered=True means included in the package
    type: str | None = None  # e.g. flush mount, matte, glossy
    size: str | None = None
    pages: int | None = None
    photos: int | None = None


class Frame(BaseModel):
    size: str | None = None
    count: int | None = None
    price_inr: int | None = None


class Casting(BaseModel):
    offered: bool | None = None
    price_inr: int | None = None
    type: str | None = None  # e.g. hand and foot, 3D frame


class StudioPackage(BaseModel):
    studio_name: str
    package_name: str | None = None
    shoot_type: ShootType
    city: str | None = None
    price_inr: int | None = Field(None, description="Total listed price in INR, GST added if the page says it is extra")
    price_text: str | None = Field(None, description="The price exactly as written on the page")
    price_assumptions: list[str] = Field(default_factory=list, description="e.g. '18% GST added to the listed ₹30,000'")
    inclusions: list[str] = Field(default_factory=list)
    extras: list[Extra] = Field(default_factory=list, description="Paid add-ons: travel, props, outfits, makeup")
    duration_hours: float | None = None
    photos_taken: int | None = None
    edited_photos: int | None = None
    delivery_days: int | None = None
    album: Album = Field(default_factory=Album)
    frames: list[Frame] = Field(default_factory=list)
    casting: Casting = Field(default_factory=Casting)
    rating_summary: str | None = None
    location: str | None = None
    contact_url: str | None = None
    source_url: str
    checked_on: date

    def display(self, field: str) -> str:
        value = getattr(self, field)
        return NOT_LISTED if value in (None, [], "") else str(value)
