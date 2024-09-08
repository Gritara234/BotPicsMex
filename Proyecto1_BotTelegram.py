import asyncio
import os
import logging
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get bot token and email credentials from environment variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
APPOINTMENT_EMAIL = os.getenv('APPOINTMENT_EMAIL')  # Your email where the form will be sent
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # Email password for authentication

if not TOKEN:
    raise ValueError("No TOKEN provided. Set TELEGRAM_BOT_TOKEN environment variable.")

if not APPOINTMENT_EMAIL or not EMAIL_PASSWORD:
    raise ValueError("No email credentials provided. Set APPOINTMENT_EMAIL and EMAIL_PASSWORD environment variables.")

# Define Prices, FAQs, Location, and Sample Photos
PRICES = {
    "Paquete Básico": "$100",
    "Paquete Estándar": "$200",
    "Paquete Premium": "$300"
}

FAQS = {
    "¿Cuál es su política de reembolsos?": "Ofrecemos un reembolso completo dentro de los 7 días posteriores a la compra.",
    "¿Viajan para sesiones de fotos?": "Sí, podemos viajar a su ubicación por un costo adicional.",
    "¿Cuánto tiempo tomará recibir las fotos?": "Recibirá sus fotos dentro de las 2 semanas posteriores a la sesión."
}

LOCATION = "Calle Arty 226"
SAMPLE_PHOTOS = [
    "https://i.imgur.com/1APLxNQ.png",
    "https://i.imgur.com/tQc3JMS.png",
    "https://i.imgur.com/KSORerQ.png",
    "https://i.imgur.com/dQtZGfg.png",
    "https://i.imgur.com/BA76eje.png",
    "https://i.imgur.com/S0BBzXu.png",
    "https://i.imgur.com/TpJWkpZ.png"

]

WELCOME_IMAGE_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSvRMOhhFEONDKXZ2Xyb8N-T1C7AAGklkGNIA&s"  # Replace with your actual welcome image URL

REVIEWS = [
    "¡Excelente servicio! Las fotos quedaron hermosas. - María G.",
    "Muy profesionales y creativos. Altamente recomendados. - Juan L.",
    "Una experiencia inolvidable. Capturaron momentos preciosos. - Ana P."
]

SOCIAL_MEDIA = {
    "Instagram": ("@picsmex_photography", "https://www.instagram.com/picsmex_photography"),
    "Facebook": ("PicsMex Photography", "https://www.facebook.com/PicsMexPhotography"),
    "Twitter": ("@PicsMexPhoto", "https://twitter.com/PicsMexPhoto")
}

PAYMENT_METHODS = [
    "Tarjeta de crédito/débito",
    "PayPal",
    "Transferencia bancaria",
    "Efectivo (solo para pagos en persona)"
]

# Define services available for appointment
SERVICES = ["Fotografía Básica", "Fotografía de Boda", "Fotografía de Retrato", "Fotografía Corporativa"]

async def start(update: Update, context) -> None:
    if 'photo_message_ids' not in context.user_data:
        context.user_data['photo_message_ids'] = []
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context) -> None:
    # Delete any existing sample photos
    await delete_sample_photos(update, context)

    keyboard = [
        [InlineKeyboardButton("Ver Precios", callback_data='prices')],
        [InlineKeyboardButton("Ver Fotos de Muestra", callback_data='samples')],
        [InlineKeyboardButton("Ubicación", callback_data='location')],
        [InlineKeyboardButton("Preguntas Frecuentes", callback_data='faqs')],
        [InlineKeyboardButton("Agendar Cita", callback_data='appntmnt')],
        [InlineKeyboardButton("Siguiente ➡️", callback_data='next_page')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = '¡Bienvenido a PicsMex Photography! ¿Cómo puedo asistirte hoy?'
    message_text = f'<a href="{WELCOME_IMAGE_URL}">&#8205;</a>{welcome_text}'

    if update.message:
        await update.message.reply_html(message_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def show_second_page(update: Update, context) -> None:
    await delete_sample_photos(update, context)

    keyboard = [
        [InlineKeyboardButton("Reseñas", callback_data='reviews')],
        [InlineKeyboardButton("Redes Sociales", callback_data='social_media')],
        [InlineKeyboardButton("Métodos de Pago", callback_data='payment_methods')],
        [InlineKeyboardButton("⬅️ Anterior", callback_data='prev_page')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    page_text = 'Página 2: Más información sobre PicsMex Photography'
    message_text = f'<a href="{WELCOME_IMAGE_URL}">&#8205;</a>{page_text}'

    await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def button_click(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()

    try:
        if query.data == 'prices':
            price_list = "\n".join([f"{pkg}: {price}" for pkg, price in PRICES.items()])
            await show_info(update, context, f"Aquí están nuestros paquetes y precios:\n\n{price_list}")
        elif query.data == 'samples':
            await query.edit_message_text(text="Aquí tienes algunas de nuestras fotos de muestra:")
            await send_sample_photos(update, context)
        elif query.data == 'location':
            await show_info(update, context, f"Nuestra ubicación:\n\n{LOCATION}")
        elif query.data == 'faqs':
            faqs = "\n\n".join([f"{question}\n{answer}" for question, answer in FAQS.items()])
            await show_info(update, context, f"Preguntas Frecuentes:\n\n{faqs}")
        elif query.data == 'appntmnt':
            await start_appointment_form(update, context)
        elif query.data == 'next_page':
            await show_second_page(update, context)
        elif query.data == 'prev_page':
            await show_main_menu(update, context)
        elif query.data == 'reviews':
            reviews_text = "\n\n".join(REVIEWS)
            await show_info(update, context, f"Reseñas de nuestros clientes:\n\n{reviews_text}")
        elif query.data == 'social_media':
            social_media_text = "\n".join([f"[{platform}]({url}) : {handle}" for platform, (handle, url) in SOCIAL_MEDIA.items()])
            await show_info(update, context, f"Síguenos en redes sociales:\n\n{social_media_text}")
        elif query.data == 'payment_methods':
            payment_methods_text = "\n".join(f"• {method}" for method in PAYMENT_METHODS)
            await show_info(update, context, f"Métodos de pago aceptados:\n\n{payment_methods_text}")
        elif query.data == 'back_to_menu':
            await show_main_menu(update, context)

    except Exception as e:
        logger.error(f"Error in button_click: {str(e)}")
        await query.edit_message_text(text="Lo siento, ocurrió un error. Por favor, inténtalo de nuevo más tarde.")

async def show_info(update: Update, context, text: str, parse_mode=ParseMode.HTML) -> None:
    keyboard = [[InlineKeyboardButton("Volver al Menú", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f'<a href="{WELCOME_IMAGE_URL}">&#8205;</a>{text}'
    
    await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode=parse_mode)

async def send_sample_photos(update: Update, context) -> None:
    chat_id = update.callback_query.message.chat_id
    context.user_data['photo_message_ids'] = []
    
    selected_photos = random.sample(SAMPLE_PHOTOS, 3)
    
    for photo_url in selected_photos:
        message = await context.bot.send_photo(chat_id=chat_id, photo=photo_url)
        context.user_data['photo_message_ids'].append(message.message_id)

async def delete_sample_photos(update: Update, context) -> None:
    if 'photo_message_ids' in context.user_data:
        chat_id = update.callback_query.message.chat_id if update.callback_query else update.message.chat_id
        for message_id in context.user_data['photo_message_ids']:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as e:
                logger.error(f"Error deleting message {message_id}: {str(e)}")
        context.user_data['photo_message_ids'] = []

async def handle_message(update: Update, context) -> None:
    user_input = update.message.text
    stage = context.user_data.get('appointment_stage')

    if stage == 'name':
        context.user_data['client_name'] = user_input
        await update.message.reply_text("Gracias. Ahora, por favor ingresa tu número de teléfono:")
        context.user_data['appointment_stage'] = 'phone'
    elif stage == 'phone':
        context.user_data['client_phone'] = user_input
        await update.message.reply_text("¿Qué servicio estás solicitando? Elige una opción:\n" +
                                        "\n".join([f"{i+1}. {service}" for i, service in enumerate(SERVICES)]))
        context.user_data['appointment_stage'] = 'service'
    elif stage == 'service':
        try:
            service_index = int(user_input) - 1
            if service_index < 0 or service_index >= len(SERVICES):
                raise ValueError
            context.user_data['client_service'] = SERVICES[service_index]
            await update.message.reply_text("Gracias. ¿Qué fecha prefieres para la cita? (Formato: DD/MM/AAAA)")
            context.user_data['appointment_stage'] = 'date'
        except ValueError:
            await update.message.reply_text("Por favor, ingresa un número válido para el servicio.")
    elif stage == 'date':
        context.user_data['client_date'] = user_input
        await update.message.reply_text("Gracias por completar el formulario. Enviando tus detalles...")

        # Send the email with the appointment data
        await send_appointment_email(context.user_data)

        await update.message.reply_text("Tu cita ha sido solicitada exitosamente. Nos pondremos en contacto contigo pronto.")
        context.user_data['appointment_stage'] = None  # Clear the stage after form submission

async def start_appointment_form(update: Update, context) -> None:
    await update.callback_query.message.reply_text("Por favor, ingresa tu nombre:")
    context.user_data['appointment_stage'] = 'name'

async def send_appointment_email(user_data) -> None:
    # Set up email content
    client_name = user_data['client_name']
    client_phone = user_data['client_phone']
    client_service = user_data['client_service']
    client_date = user_data['client_date']

    subject = f"Solicitud de Cita de {client_name}"
    body = (f"Nombre del Cliente: {client_name}\n"
            f"Teléfono: {client_phone}\n"
            f"Servicio Solicitado: {client_service}\n"
            f"Fecha de la Cita: {client_date}")

    # Compose the email
    msg = MIMEMultipart()
    msg['From'] = APPOINTMENT_EMAIL
    msg['To'] = APPOINTMENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Send the email
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(APPOINTMENT_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
        logging.info(f"Appointment email sent successfully to {APPOINTMENT_EMAIL}")
    except Exception as e:
        logging.error(f"Failed to send appointment email: {str(e)}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Register command and callback handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
