from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.client import Client  # noqa: E402, F401
from app.models.input_item import InputItem  # noqa: E402, F401
from app.models.input_item_edit import InputItemEdit  # noqa: E402, F401
from app.models.generation import Generation  # noqa: E402, F401
from app.models.generation_result import GenerationResult  # noqa: E402, F401
from app.models.channel_setting import ChannelSetting  # noqa: E402, F401
