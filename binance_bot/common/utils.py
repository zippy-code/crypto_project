import telegram

token = "6021700635:AAHYxX46jIYMgnqFKrZy3FtaVOmM5gpIfUM"
chat_id = "5866978788"

bot = telegram.Bot(token)
text = '나도 잘 부탁'
bot.sendMessage(chat_id, text)
