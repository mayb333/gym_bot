from aiogram.dispatcher.filters.state import State, StatesGroup


class WeightState(StatesGroup):
    weight = State()
    _continue = State()


class ProductState(StatesGroup):
    category = State()
    product = State()
    product_weight = State()
    _continue = State()
    repeat = State()