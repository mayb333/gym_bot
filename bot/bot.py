import os
import random
import json
import time

from config import TOKEN
from greeting import greeting

from datetime import datetime
from datetime import date

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from states import WeightState, ProductState
from db import DataBase


bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())
db = DataBase()


@dp.message_handler(commands='start')
async def start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
    await message.answer(greeting, reply_markup=keyboard)


@dp.message_handler(Text(equals='Функции'))
async def show_functions(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Записать вес').insert('Записать прием пищи') \
                                                                .row('Выгрузить данные').insert('Мотивирующее фото')
    await message.answer('<b>Выберите фунцию </b>', reply_markup=keyboard)


@dp.message_handler(Text(equals='Записать вес'), state=None)
async def enter_write_weight(message: types.Message):
    """
    Requesting for writing weight
    """
    await WeightState.weight.set()
    await message.answer('Введите свой вес (десятичные разделитель - точка)', reply_markup=types.ReplyKeyboardRemove())


# get user's weight for the date
@dp.message_handler(state=WeightState.weight)
async def get_weight_from_user(message: types.Message, state: FSMContext):
    """
    Get response from user (weight)
    """

    # saving message id, for deleting these messages later
    msg_id = message.message_id
    await state.update_data(msg_id=msg_id)

    try:
        weight = message.text.strip()
        weight = '%.2f' % float(weight)
        await state.update_data(weight=weight)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Да').add('Нет')
        await message.answer(f'Хотите внести {weight} в базу данных?', reply_markup=keyboard)
        await WeightState.next()
    except Exception:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
        await message.answer('❌ Введено некорректное значение веса.\nПопробуйте еще раз.', reply_markup=keyboard)
        await state.finish()

        # delete unnecessary messages
        time.sleep(2)
        await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, 1)))


@dp.message_handler(state=WeightState._continue)
async def write_weigt_to_db(message: types.Message, state: FSMContext):
    """
    Check if the user wants to continue writing his weight into db
    """
    answer2 = message.text
    state_data = await state.get_data()
    msg_id = state_data.get('msg_id')

    if answer2 == 'Да':

        weight = state_data.get('weight')
        user_id = message.from_user.id
        date_day = date.today()

        if db.user_not_in_weights_for_certain_date(date_day, user_id):
            db.write_to_weights(date_day, user_id, weight)

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
            await message.answer(f'✅ Вес {weight} для даты {date_day} записан в базу данных!', reply_markup=keyboard)

        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
            await message.answer(f'❗ Вес для даты {date_day} уже записан в базу данных️', reply_markup=keyboard)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
        await message.answer('❌ Запись веса была отменена.', reply_markup=keyboard)

    # delete unnecessary messages
    time.sleep(2)
    await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, 3)))

    await state.finish()


@dp.message_handler(Text(equals='Записать прием пищи'), state=None)
async def show_categories(message: types.Message):
    """
    Requesting for writing meal (offering to choose a category)
    """

    with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
        products_data = json.load(file)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    categories = products_data.keys()
    for category in categories:
        keyboard.add(category)

    await ProductState.category.set()
    await message.answer('Выберите категорию', reply_markup=keyboard)


@dp.message_handler(state=ProductState.category)
async def get_products_category(message: types.Message, state: FSMContext):
    category = message.text
    msg_id = message.message_id
    state_data = await state.get_data()
    repeat = state_data.get('repeat')

    with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
        products_data = json.load(file)
    categories = products_data.keys()
    if category in categories:
        await state.update_data(category=category)
        await state.update_data(msg_id=msg_id)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for item in products_data[category]:
            product_name = item['название']
            keyboard.add(product_name)

        await message.answer('Выберите продукт', reply_markup=keyboard)
        await ProductState.next()
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
        await message.answer('❌ Введена некорректная категория. \nПопробуйте еще раз.', reply_markup=keyboard)
        if repeat:
            await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
        await state.finish()

        # delete unnecessary messages
        time.sleep(2)
        if not repeat:
            await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, -1)))
        await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-1, 1)))


@dp.message_handler(state=ProductState.product)
async def get_product_name(message: types.Message, state: FSMContext):
    product_name = message.text

    with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
        products_data = json.load(file)

    state_data = await state.get_data()
    category = state_data.get('category')
    msg_id = state_data.get('msg_id')
    repeat = state_data.get('repeat')

    product_is_in_products_data = False
    for item in products_data[category]:
        if item['название'] == product_name:
            product_is_in_products_data = True

    if product_is_in_products_data:
        await state.update_data(product_name=product_name)
        await message.answer('Введите количество употребленных грамм <u>(десятичный разделитель - точка)</u>',
                             reply_markup=types.ReplyKeyboardRemove())
        await ProductState.next()
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
        await message.answer('❌ Введено неверное название продукта. \nПопробуйте еще раз.', reply_markup=keyboard)
        if repeat:
            await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
        await state.finish()

        # delete unnecessary messages
        time.sleep(2)
        if not repeat:
            await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, -1)))
        await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-1, 3)))


@dp.message_handler(state=ProductState.product_weight)
async def get_product_weight(message: types.Message, state: FSMContext):
    product_weight = message.text.strip()
    state_data = await state.get_data()
    product_name = state_data.get('product_name')
    msg_id = state_data.get('msg_id')
    repeat = state_data.get('repeat')

    try:
        product_weight = '%.1f' % float(product_weight)
        await state.update_data(product_weight=product_weight)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Да').add('Нет')
        await message.answer(f'Хотите записать \'{product_name}\' с весом {product_weight} грамм в базу данных?',
                             reply_markup=keyboard)

        await ProductState.next()
    except Exception:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
        await message.answer('❌ Введено некорректное значение массы продукта. \nПопробуйте еще раз.',
                             reply_markup=keyboard)
        if repeat:
            await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
        await state.finish()

        # delete unnecessary messages
        time.sleep(2)
        if not repeat:
            await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, -1)))
        await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-1, 5)))


@dp.message_handler(state=ProductState._continue)
async def write_product_weight_to_db(message: types.Message, state: FSMContext):
    answer = message.text
    state_data = await state.get_data()
    repeat = state_data.get('repeat')

    if answer == 'Да':
        """Записать в бд"""

        product_category = state_data.get('category')
        product_name = state_data.get('product_name')
        product_weight = float(state_data.get('product_weight'))
        user_id = message.from_user.id
        date_day = date.today()
        datetime_day = datetime.now()

        with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
            products_data = json.load(file)

        proteins_per_100_grams = 0
        for item in products_data[product_category]:
            if item['название'] == product_name:
                proteins_per_100_grams = float(item['белки'])

        product_proteins = product_weight * proteins_per_100_grams / 100
        product_proteins = '%.1f' % product_proteins
        meal_id = db.set_meal_id(date_day, user_id)

        if repeat:
            """
            if this is not first state running ('write_more_product_for_meal' func resets states and runs this again)
            then 'repeat' key will be available in state.get_data()
            This means that we need to add product to the same meal_id as the previous product has
            """
            db.write_to_proteins(date=date_day, datetime=datetime_day, user_id=user_id, meal_id=meal_id,
                                 meal_name=product_name, grams=product_weight, proteins=product_proteins)
        else:
            meal_id += 1
            db.write_to_proteins(date=date_day, datetime=datetime_day, user_id=user_id, meal_id=meal_id,
                                 meal_name=product_name, grams=product_weight, proteins=product_proteins)

        await message.answer(f'✅ Продукт {product_name} с {product_proteins} г белка весом {product_weight} г '
                             f'<b> успешно записан в бд! </b>')
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Да').add('Нет')
        await message.answer('Хотите записать еще продукт в этот прием пищи?', reply_markup=keyboard)
        await ProductState.next()

    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
        await message.answer('❌ Запись была отменена.', reply_markup=keyboard)
        if repeat:
            await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
        await state.finish()

    # delete unnecessary messages
    msg_id = state_data.get('msg_id')
    time.sleep(2)
    if not repeat:
        await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, -1)))
    await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-1, 7)))



@dp.message_handler(state=ProductState.repeat)
async def write_more_product_for_meal(message: types.Message, state: FSMContext):
    write_more_product_to_meal = message.text
    msg_id = message.message_id

    if write_more_product_to_meal == 'Да':
        with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
            products_data = json.load(file)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        categories = products_data.keys()
        for category in categories:
            keyboard.add(category)

        await state.update_data(repeat=write_more_product_to_meal)
        await ProductState.category.set()
        await message.answer('Выберите категорию', reply_markup=keyboard)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
        await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
        await state.finish()
        # delete unnecessary messages
        time.sleep(2)
        await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-1, 1)))


@dp.message_handler(Text(equals='Мотивирующее фото'))
async def send_motivational_photo(message: types.Message):
    msg_id = message.message_id
    number = random.randint(1, 4)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
    with open(f'bot/photos/mem_{number}.jpg', 'rb') as photo:
        await bot.send_photo(chat_id=message.chat.id, photo=photo, reply_markup=keyboard)

    # delete unnecessary messages
    time.sleep(2)
    await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-2, 0)))


@dp.message_handler(Text(equals='Выгрузить данные'))
async def get_data_from_db(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Данные о приемах пищи').insert('Данные о весе')
    await message.answer('<b>Выберите, какие данные вы хотите выгрузить</b>', reply_markup=keyboard)


@dp.message_handler(Text(equals='Данные о весе'))
async def get_weights_data_from_db(message: types.Message):
    user_id = message.from_user.id
    date_day = date.today()
    msg_id = message.message_id

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')

    output = db.import_from_weights_sql_to_csv(user_id=user_id, date=date_day)
    if output == 'File is created':
        with open(f'bot/users_csv_data/weights_data_{user_id}_{date_day}.csv', 'rb') as file:
            await message.answer('✅')
            await message.reply_document(file, reply_markup=keyboard)

        # delete user's file, that was created
        os.remove(f'bot/users_csv_data/weights_data_{user_id}_{date_day}.csv')

    elif output == 'No data found':
        await message.answer('❌ Похоже вы не записали никаких данных о весе', reply_markup=keyboard)
    elif output == 'Problem occurred':
        await message.answer('❌ Произошла ошибка', reply_markup=keyboard)

    # delete unnecessary messages
    time.sleep(2)
    await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, 0)))


@dp.message_handler(Text(equals='Данные о приемах пищи'))
async def get_proteins_data_from_db(message: types.Message):
    user_id = message.from_user.id
    date_day = date.today()
    msg_id = message.message_id

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')

    output = db.import_from_proteins_sql_to_csv(user_id=user_id, date=date_day)
    if output == 'File is created':
        with open(f'bot/users_csv_data/proteins_data_{user_id}_{date_day}.csv', 'rb') as file:
            await message.answer('✅')
            await message.reply_document(file, reply_markup=keyboard)

        # delete user's file, that was created
        os.remove(f'bot/users_csv_data/proteins_data_{user_id}_{date_day}.csv')

    elif output == 'No data found':
        await message.answer('❌ Похоже вы не записали никаких данных о ваших приемах пищи', reply_markup=keyboard)
    elif output == 'Problem occurred':
        await message.answer('❌ Произошла ошибка', reply_markup=keyboard)

    # delete unnecessary messages
    time.sleep(2)
    await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, 0)))


async def delete_messages(message, msg_id,  int_range: list):
    for number in int_range:
        await bot.delete_message(chat_id=message.chat.id, message_id=msg_id + number)


def main():
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()