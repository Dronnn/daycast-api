from pydantic import BaseModel


class GenerationSettingsRequest(BaseModel):
    custom_instruction: str | None = None
    separate_business_personal: bool = False


class GenerationSettingsResponse(BaseModel):
    custom_instruction: str | None = None
    separate_business_personal: bool = False

    model_config = {"from_attributes": True}
