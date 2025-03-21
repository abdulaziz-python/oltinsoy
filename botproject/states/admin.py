from aiogram.fsm.state import State, StatesGroup

class TaskState(StatesGroup):
    title = State()
    description = State()
    deadline = State()
    mahallas = State()
    confirm = State()

class GradingState(StatesGroup):
    percentage = State()
    comment = State()

class BroadcastState(StatesGroup):
    title = State()
    message = State()
    target = State()
    district = State()
    mahalla = State()
    confirm = State()

