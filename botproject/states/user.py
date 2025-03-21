from aiogram.fsm.state import State, StatesGroup

class LoginState(StatesGroup):
    phone_number = State()
    jshir = State()

class TaskState(StatesGroup):
    confirm_completion = State()
    report_description = State()
    report_files = State()


class TaskSubmissionState(StatesGroup):
    comment = State()
    files = State()