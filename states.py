from aiogram.fsm.state import State, StatesGroup


class BookStates(StatesGroup):
    waiting_title = State()
    waiting_author = State()
    waiting_description = State()
    waiting_poster = State()
    waiting_file = State()
    waiting_edit = State()


class BroadcastStates(StatesGroup):
    waiting_type = State()
    waiting_text = State()
    waiting_image = State()
    waiting_button_text = State()
    waiting_button_url = State()
    waiting_forward_message = State()
    waiting_confirm = State()


class TriggerStates(StatesGroup):
    waiting_keywords = State()
    waiting_action = State()
    waiting_value = State()
    waiting_edit = State()


class ModerationStates(StatesGroup):
    waiting_user = State()
    waiting_reason = State()
    waiting_duration = State()


class AdminStates(StatesGroup):
    waiting_admin_id = State()


class DonatorStates(StatesGroup):
    waiting_name = State()
    waiting_username = State()
    waiting_comment = State()


class VideoStates(StatesGroup):
    waiting_forward_message = State()
    waiting_confirm = State()