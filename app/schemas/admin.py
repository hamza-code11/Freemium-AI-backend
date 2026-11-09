from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


class AdminLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AdminForgotPassword(BaseModel):
    email: EmailStr


class AdminResetPassword(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def check_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")
        return self


class AdminChangePassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def check_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")
        return self


class AdminResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    image: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)