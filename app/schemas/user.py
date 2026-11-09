from datetime import datetime
from app.schemas.target_audience import TargetAudience
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
    model_validator,
    field_validator
)


def _check_bcrypt_len(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 bytes")
    return value



class VerifyPasswordResetOTP(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")

        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")

        return self



class BusinessProfileCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=True)

    business_name: str = Field(min_length=2, max_length=150)
    business_type: str = Field(min_length=2, max_length=100)
    services: str = Field(min_length=2, max_length=2000)
    target_audience: list[TargetAudience] = Field(min_length=1, max_length=12)
    business_goals: str | None = Field(default=None, max_length=2000)
    business_description: str | None = Field(default=None, max_length=5000)

    @field_validator("target_audience")
    @classmethod
    def unique_target_audience(cls, v):
        return list(dict.fromkeys(v))


class BusinessProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=True)

    business_name: str | None = Field(default=None, min_length=2, max_length=150)
    business_type: str | None = Field(default=None, min_length=2, max_length=100)
    services: str | None = Field(default=None, min_length=2, max_length=2000)
    target_audience: list[TargetAudience] | None = Field(default=None, min_length=1, max_length=12)
    business_goals: str | None = Field(default=None, max_length=2000)
    business_description: str | None = Field(default=None, max_length=5000)

    @field_validator("business_name", "business_type", "services", "target_audience", mode="before")
    @classmethod
    def required_fields_not_null(cls, v):
        if v is None:
            raise ValueError("This field cannot be null")
        return v

    @field_validator("target_audience")
    @classmethod
    def unique_target_audience(cls, v):
        if v is None:
            return v
        return list(dict.fromkeys(v))


class BusinessProfileResponse(BaseModel):
    id: int
    business_name: str
    business_type: str
    services: str
    target_audience: list[str] = []
    business_goals: str | None = None
    business_description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("target_audience", mode="before")
    @classmethod
    def normalize_target_audience(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


    

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    business: BusinessProfileCreate

    @field_validator("password")
    @classmethod
    def password_bytes(cls, v):
        return _check_bcrypt_len(v)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    image: str | None = None
    created_at: datetime
    business_profiles: list[BusinessProfileResponse] = []

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)




class ResetPassword(BaseModel):
    reset_token: str = Field(min_length=20)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")

        return self

    