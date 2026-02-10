from pydantic import BaseModel


class ChannelSettingItem(BaseModel):
    channel_id: str
    is_active: bool = True
    default_style: str = "casual"
    default_language: str = "ru"
    default_length: str = "medium"


class ChannelSettingsRequest(BaseModel):
    channels: list[ChannelSettingItem]


class ChannelSettingResponse(BaseModel):
    channel_id: str
    is_active: bool
    default_style: str
    default_language: str
    default_length: str

    model_config = {"from_attributes": True}
