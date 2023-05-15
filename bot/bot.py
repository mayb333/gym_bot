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

from states import WeightState, ProductState, SendingDataState
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
                                                                .row('Выгрузить данные')
    await message.answer('<b>Выберите фунцию </b>', reply_markup=keyboard)


@dp.message_handler(Text(equals='Записать вес'), state=None)
async def enter_write_weight(message: types.Message):
    """
    Requesting for writing weight
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('🚫 Отмена')
    await WeightState.weight.set()
    await message.answer('Введите свой вес в кг (десятичные разделитель - точка)', reply_markup=keyboard)


@dp.message_handler(state=WeightState.weight)
async def get_weight_from_user(message: types.Message, state: FSMContext):
    """
    Get response from user (weight)
    """

    # saving message id, for deleting unnecessary messages later
    msg_id = message.message_id
    await state.update_data(msg_id=msg_id)

    message_text = message.text.strip()
    if message_text == '🚫 Отмена':
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
        await message.answer('🚫 Запись веса была отменена.', reply_markup=keyboard)
        await state.finish()

        # delete unnecessary messages
        time.sleep(2)
        await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, 1)))
    else:
        try:
            weight = float(message_text)
            limit_weight = 250
            if weight < limit_weight:
                weight = '%.2f' % weight
                await state.update_data(weight=weight)

                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Да').insert('Нет')
                await message.answer(f'❓ Хотите внести {weight} в базу данных?', reply_markup=keyboard)
                await WeightState.next()
            else:
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
                await message.answer('❌ Введено некорректное значение веса.\nПопробуйте еще раз.',
                                     reply_markup=keyboard)
                await state.finish()

        except Exception:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
            await message.answer('❌ Введено некорректное значение веса.\nПопробуйте еще раз.', reply_markup=keyboard)
            await state.finish()

            # delete unnecessary messages
            time.sleep(2)
            await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, 1)))


@dp.message_handler(state=WeightState._continue)
async def write_weight_to_db(message: types.Message, state: FSMContext):
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
        await message.answer('🚫 Запись веса была отменена.', reply_markup=keyboard)

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

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('🚫 Отмена')
    categories = products_data.keys()
    for i, category in enumerate(categories):
        if i % 2 == 0:
            keyboard.row(category)
        else:
            keyboard.insert(category)

    await ProductState.category.set()
    await message.answer('Выберите категорию', reply_markup=keyboard)


@dp.message_handler(state=ProductState.category)
async def get_products_category(message: types.Message, state: FSMContext):
    """
    Saving product_category and offering to choose a product
    """
    category = message.text.strip()
    msg_id = message.message_id
    state_data = await state.get_data()
    repeat = state_data.get('repeat')

    with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
        products_data = json.load(file)
    categories = products_data.keys()
    if category in categories:
        await state.update_data(category=category)
        await state.update_data(msg_id=msg_id)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('↩️ Назад').insert('🚫 Отмена')
        for i, item in enumerate(products_data[category]):
            product_name = item['название']
            if i % 2 == 0:
                keyboard.row(product_name)
            else:
                keyboard.insert(product_name)

        await message.answer('Выберите продукт', reply_markup=keyboard)
        await ProductState.next()
    else:
        if category == '🚫 Отмена':
            message_to_send = '🚫 Запись продукта была отменена.'
        else:
            message_to_send = '❌ Введена некорректная категория. \nПопробуйте еще раз.'

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
        await message.answer(message_to_send, reply_markup=keyboard)
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
    """
    Saving product name and offering to write grams of eaten product
    """
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
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('↩️ Назад').insert('🚫 Отмена')
        await message.answer('Введите количество употребленных грамм <u>(десятичный разделитель - точка)</u>',
                             reply_markup=keyboard)
        await ProductState.next()

    else:
        if product_name == '🚫 Отмена' or (product_name != '🚫 Отмена' and product_name != '↩️ Назад'):
            if product_name == '🚫 Отмена':
                message_to_send = '🚫 Запись продукта была отменена.'
            else:
                message_to_send = '❌ Введено неверное название продукта. \nПопробуйте еще раз.'

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
            await message.answer(message_to_send, reply_markup=keyboard)
            if repeat:
                await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
            await state.finish()
        elif product_name == '↩️ Назад':
            with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
                products_data = json.load(file)

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('🚫 Отмена')
            categories = products_data.keys()
            for i, category in enumerate(categories):
                if i % 2 == 0:
                    keyboard.row(category)
                else:
                    keyboard.insert(category)

            await ProductState.category.set()
            await message.answer('Выберите категорию', reply_markup=keyboard)

        # delete unnecessary messages
        try:
            time.sleep(2)
            if not repeat:
                await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, -1)))
            await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-1, 3)))
        except Exception:
            msg_id = message.message_id
            await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-3, 1)))


@dp.message_handler(state=ProductState.product_weight)
async def get_product_weight(message: types.Message, state: FSMContext):
    """
    Saving product weight and asking if a user wants to write this product to database
    """
    message_text = message.text.strip()
    state_data = await state.get_data()
    product_name = state_data.get('product_name')
    category = state_data.get('category')
    msg_id = state_data.get('msg_id')
    repeat = state_data.get('repeat')
    limit_products_weight = 2000

    # if message_text == '🚫 Отмена':
    #     keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
    #     await message.answer('🚫 Запись продукта была отменена.', reply_markup=keyboard)
    #
    #     if repeat:
    #         await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
    #     await state.finish()
    #
    # else:
    try:
        product_weight = float(message_text)
        if product_weight < limit_products_weight:
            product_weight = '%.1f' % product_weight
            await state.update_data(product_weight=product_weight)

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Да').insert('Нет')
            await message.answer(f'❓ Хотите записать \'{product_name}\' с весом {product_weight} грамм в базу '
                                 f'данных?', reply_markup=keyboard)
            await ProductState.next()
        # if there is an impossible product weight that couldn't have been eaten
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
            await message.answer('❌ Введено некорректное значение массы продукта. \nПопробуйте еще раз.',
                                 reply_markup=keyboard)
            if repeat:
                await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
            await state.finish()
    # If there is no float message
    except Exception:
        if message_text == '🚫 Отмена':
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
            await message.answer('🚫 Запись продукта была отменена.', reply_markup=keyboard)

            if repeat:
                await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
            await state.finish()

        elif message_text == '↩️ Назад':
            with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
                products_data = json.load(file)
            categories = products_data.keys()
            if category in categories:
                await state.update_data(category=category)
                await state.update_data(msg_id=msg_id)

                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('↩️ Назад').insert('🚫 Отмена')
                for i, item in enumerate(products_data[category]):
                    product_name = item['название']
                    if i % 2 == 0:
                        keyboard.row(product_name)
                    else:
                        keyboard.insert(product_name)

                await message.answer('Выберите продукт', reply_markup=keyboard)
                await ProductState.product.set()
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
            await message.answer('❌ Введено некорректное значение массы продукта. \nПопробуйте еще раз.',
                                 reply_markup=keyboard)
            if repeat:
                await message.answer('✅ Прием пищи сохранен.', reply_markup=keyboard)
            await state.finish()

        # delete unnecessary messages
        time.sleep(2)
        msg_id = message.message_id
        await delete_messages(message, msg_id=msg_id, int_range=list(range(-3, 1)))


@dp.message_handler(state=ProductState._continue)
async def write_product_weight_to_db(message: types.Message, state: FSMContext):
    """
    Writing to db and asking if a user wants to write more product to the meal
    """
    answer = message.text
    state_data = await state.get_data()
    repeat = state_data.get('repeat')

    if answer == 'Да':
        # write to db

        product_category = state_data.get('category')
        product_name = state_data.get('product_name')
        product_weight = float(state_data.get('product_weight'))
        user_id = message.from_user.id
        date_day = date.today()
        datetime_day = datetime.now()

        with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
            products_data = json.load(file)

        proteins_per_100_grams, carbs_per_100_grams, fats_per_100_grams = 0, 0, 0
        for item in products_data[product_category]:
            if item['название'] == product_name:
                proteins_per_100_grams = float(item['белки'])
                carbs_per_100_grams = float(item['белки'])
                fats_per_100_grams = float(item['белки'])

        product_proteins = '%.1f' % (product_weight * proteins_per_100_grams / 100)
        product_carbs = '%.1f' % (product_weight * carbs_per_100_grams / 100)
        product_fats = '%.1f' % (product_weight * fats_per_100_grams / 100)

        meal_id = db.set_meal_id(date_day, user_id)

        if repeat:
            """
            if this is not first state running ('write_more_product_for_meal' func resets states and runs this again)
            then 'repeat' key will be available in state.get_data()
            This means that we need to add product to the same meal_id as the previous product has
            """
            db.write_to_proteins(date=date_day, datetime=datetime_day, user_id=user_id, meal_id=meal_id,
                                 meal_name=product_name, grams=product_weight, proteins=product_proteins,
                                 carbs=product_carbs, fats=product_fats)
        else:
            meal_id += 1
            db.write_to_proteins(date=date_day, datetime=datetime_day, user_id=user_id, meal_id=meal_id,
                                 meal_name=product_name, grams=product_weight, proteins=product_proteins,
                                 carbs=product_carbs, fats=product_fats)

        await message.answer(f'✅ Продукт {product_name} с {product_proteins} г белка весом {product_weight} г '
                             f'<b> успешно записан в бд! </b>')
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Да').insert('Нет')
        await message.answer('❓ Хотите записать еще продукт в этот прием пищи?', reply_markup=keyboard)
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
    try:
        if not repeat:
            await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, -1)))
        await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-1, 7)))
    except Exception:
        print('[INFO] Couldn\'t delete messages')


@dp.message_handler(state=ProductState.repeat)
async def write_more_product_for_meal(message: types.Message, state: FSMContext):
    """
    If received yes, state will be set to category and this whole form will appear again
    """
    write_more_product_to_meal = message.text
    msg_id = message.message_id

    if write_more_product_to_meal == 'Да':
        with open('bot/proteins_data.json', 'r', encoding='utf-8') as file:
            products_data = json.load(file)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('🚫 Отмена')
        categories = products_data.keys()
        for i, category in enumerate(categories):
            if i % 2 == 0:
                keyboard.row(category)
            elif i % 2 == 1:
                keyboard.insert(category)

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


@dp.message_handler(Text(equals='Выгрузить данные'), state=None)
async def get_data_from_db(message: types.Message):
    """
    Asking what data table a user wants
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Данные о приемах пищи').insert('Данные о весе')\
        .insert('🚫 Отмена')
    await message.answer('<b>Выберите, какие данные вы хотите выгрузить</b>', reply_markup=keyboard)
    await SendingDataState.table.set()


@dp.message_handler(state=SendingDataState.table)
async def send_data_from_db(message: types.Message, state: FSMContext):
    """
    Sending user's (weight or proteins) data
    """
    user_id = message.from_user.id
    date_day = date.today()
    msg_id = message.message_id
    message_text = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Функции')
    table = ''

    try:
        if message_text == '🚫 Отмена':
            output = '🚫 Отмена'
        elif message_text == 'Данные о весе':
            output = db.import_from_weights_sql_to_csv(user_id=user_id, date=date_day)
            table = 'weights'
        elif message_text == 'Данные о приемах пищи':
            output = db.import_from_proteins_sql_to_csv(user_id=user_id, date=date_day)
            table = 'proteins'
        else:
            output = 'Некорректное сообщение'

        if output == 'File is created':
            with open(f'bot/users_csv_data/{table}_data_{user_id}_{date_day}.csv', 'rb') as file:
                await message.answer('✅')
                await message.reply_document(file, reply_markup=keyboard)

            # delete user's file, that was created
            os.remove(f'bot/users_csv_data/{table}_data_{user_id}_{date_day}.csv')

        elif output == 'No data found':
            await message.answer('❌ Похоже вы не записали никаких данных о весе', reply_markup=keyboard)
        elif output == 'Problem occurred':
            await message.answer('❌ Произошла ошибка', reply_markup=keyboard)
        elif output == '🚫 Отмена':
            await message.answer('🚫 Выгрузка данных была отменена.', reply_markup=keyboard)
        else:
            await message.answer('❌ Получено некорректное сообщение.', reply_markup=keyboard)

    except Exception as exp:
        print(f'[INFO] {exp}')
        await message.answer('❌ Произошла ошибка.', reply_markup=keyboard)

    await state.finish()

    # delete unnecessary messages
    time.sleep(2)
    await delete_messages(message=message, msg_id=msg_id, int_range=list(range(-4, 1)))


async def delete_messages(message, msg_id,  int_range: list):
    """
    Function for deleting unnecessary messages
    """
    for number in int_range:
        await bot.delete_message(chat_id=message.chat.id, message_id=msg_id + number)


def main():
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()
