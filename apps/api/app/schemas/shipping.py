"""Checkout address contract. US launch policy is explicit, not a silent default."""
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

US_REGIONS = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY AS GU MP PR VI AA AE AP".split())


class ShippingAddress(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    recipient_name: str = Field(min_length=2, max_length=100)
    line1: str = Field(min_length=5, max_length=120)
    line2: str = Field(default="", max_length=120)
    city: str = Field(min_length=2, max_length=80)
    region: str = Field(min_length=2, max_length=80)
    postal_code: str = Field(min_length=3, max_length=20)
    country: str = Field(min_length=2, max_length=2)
    phone: str = Field(min_length=7, max_length=30)

    @field_validator("country", "region", mode="before")
    @classmethod
    def upper_codes(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def launch_market_policy(self):
        if self.country != "US":
            raise ValueError("Shipping to this country is not available yet")
        if self.region not in US_REGIONS:
            raise ValueError("Select a valid US state or territory")
        if not re.fullmatch(r"[0-9]{5}(?:-[0-9]{4})?", self.postal_code):
            raise ValueError("Enter a valid US ZIP or ZIP+4 code")
        digits = re.sub(r"[\s().+-]", "", self.phone)
        if not digits.isascii() or not digits.isdigit():
            raise ValueError("Enter a valid US phone number")
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("Enter a ten-digit US phone number")
        self.phone = "+1" + digits
        if "address pending" in self.line1.lower():
            raise ValueError("A real delivery address is required")
        return self

    def display_address(self) -> str:
        return ", ".join(value for value in (self.recipient_name, self.line1, self.line2, self.city, self.region, self.postal_code, self.country) if value)
