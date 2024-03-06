# Импортируем нужные библиотеки
import telebot
import logging
from config import TOKEN
from telebot.types import Message, ReplyKeyboardMarkup
from gpt import MAX_TASK_TOKENS, count_tokens, ask_gpt

# Создаем бота
bot = telebot.TeleBot(TOKEN)

text_help = """Список доступных команд:
/start - начать/продолжить работу помощника
/help - вывести справочную информацию о боте
/about - вывести немного информации обо мне - давай познакомимся:)

А вот основные пояснения по использованию бота:
- Бот любит отвечать на вопросы рифмованными строчками:)
- После запуска бота вы можете начать задавать боту-помощнику какие-либо вопросы по литературе - для этого после старта нажмите на кнопку solve_task
- Вы можете задавать любые вопросы по тематике
- Иногда вопрос может получиться слишком большим и бот не сможет воспринять так много текста. Тогда бот попросит вас сократить запрос
- Пожалуйста, постарайтесь излагать свои мысли четко и кратко
- После ответа на вопрос, вам будет предложено либо продолжить объяснение, либо начать новую задачу, либо завершить ветвь вопросов - выберите вариант, который посчитаете нужным."""

commandss = ['/help', '/about', '/start', '/solve_task', '/continue', '/finish']

# Словарь с задачами и ответами
user_history = {'task': {}, 'answer': {}}

logging.basicConfig(
    level = logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='log_file.txt',
    filemode='w',
)
 
# Функция создания клавиатуры с переданными кнопками
def make_keyboard(buttons):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(*buttons)
    return markup

# def send_debug_logs(chat_id):
#     try:
#         with open('gpt_debug_logs.txt', 'rb') as log_file:
#             bot.send_document(chat_id, log_file)
#     except Exception as e:
#         print(f"Error sending debug logs: {e}")
#         bot.send_message(chat_id, 'Произошла ошибка при отправке файла с логами.')

# Обработчики команд:
@bot.message_handler(commands=['help'])
def say_help(message: Message):
    bot.send_message(message.from_user.id, text_help)

@bot.message_handler(commands=['about'])
def about_command(message: Message):
    bot.send_message(message.from_user.id, 'Давай я расскажу тебе немного о себе: Я - твой бот-помощник, готовый помочь и ответить на любой вопрос в сфере поэзии. Занимаясь высокотехнологичными науками, мы забываем о прекрасном и не менее высоком - стихах. Так что если ты захочешь прочитать какое-нибудь стихотворение или узнать что-то новое из литературы - просто задай мне вопрос. Я не оставлю тебя в одиночестве;)',
                     reply_markup=make_keyboard(['/start', '/help']))

# @bot.message_handler(commands=['debug'])
# def debug_command(message: Message):
#     send_debug_logs(message.from_user.id)

# @bot.message_handler(commands=['logs'])
# def logs_command(message: Message):
#     send_debug_logs(message.from_user.id)

@bot.message_handler(commands=['start'])
def start(message: Message):
    user_name = message.from_user.first_name
    bot.send_message(message.chat.id,
                     text=f'Привет, {user_name}! Я твой бот-помощник в литературе. Скорее задавай вопросы, а я постараюсь на них ответить! Для начала нажми на кнопку /solve_task!',
                     reply_markup=make_keyboard(['/solve_task', '/help', '/about']))
    logging.info('Отправка приветственного сообщения')

@bot.message_handler(commands=['solve_task'])
def solve_task(message: Message):
    bot.send_message(message.chat.id, 'Напиши условие следующей задачи:')
    bot.register_next_step_handler(message, handle)  

@bot.message_handler(commands=['continue'])
def continue_explanation(message):
    user_id = message.from_user.id
    if message.content_type != 'text':
        logging.info('Error - Неверный формат данных')
        bot.send_message(user_id, 'Пока я умею работать только с текстовыми сообщениями. Пожалуйста, отправьте сообщение именно текстом.')
        bot.register_next_step_handler(message, continue_explanation)
        return
    # user_request = message.text
    bot.send_message(message.from_user.id, 'Давайте продолжим.')
    bot.register_next_step_handler(message, handle)
   
@bot.message_handler(commands=['finish'])
def end_task(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Текущее решение завершено. Хотите начать заново?', reply_markup=make_keyboard(['/start', '/help']))
    user_history['task'][user_id] = None
    user_history['answer'][user_id] = None

# Обработка текстовых сообщений
@bot.message_handler(content_types=['text'], func=lambda message: message not in commandss)
def handle(message):
    user_id = message.from_user.id
    if count_tokens(message.text) <= MAX_TASK_TOKENS:
        bot.send_message(message.chat.id, 'Подождите немного...')
        answer = ask_gpt(message.text)
        user_history['task'][user_id] = message.text
        user_history['answer'][user_id] = answer
        if answer == None: # ответ с ошибкой
            bot.send_message(message.chat.id, 'Не удалось получить ответ от нейросети.',
                             reply_markup=make_keyboard(['/solve_task', '/continue']))
        elif answer == '': # пустой ответ
            bot.send_message(message.chat.id, 'Не удалось сформулировать ответ. Муза не пришла.',
                             reply_markup=make_keyboard(['/solve_task']))
            logging.info(f'Действие: {message.text}, Результат: Error - пустой ответ от нейросети.')
        else: # ответ без ошибок
            bot.send_message(message.chat.id, answer,
                             reply_markup=make_keyboard(['/solve_task', '/continue', '/finish']))
    else:
        user_history['task'][user_id] = None
        user_history['answer'][user_id] = None
        bot.send_message(message.chat.id, 'Запрос превышает максимальное количество символов. Пожалуйста, отправьте запрос покороче.')
        logging.info(f'Действие: {message.text}, Результат: Error - Текст задачи слишком длинный.')

bot.polling()
