import socket

def get_ip_address():
    """Получаем текущий IP адрес машины"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Подключаемся к гугловскому DNS для определения интерфейса
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'  # Если ошибка, значит локалхост
    finally:
        s.close()
    return ip

# Определяем IP продакшн сервера
PROD_SERVER_IP = '188.253.17.60'

# Текущий IP нашей машины
CURRENT_IP = get_ip_address()

# Проверяем, где запущен бот
if CURRENT_IP == PROD_SERVER_IP:
    # Мы на продакшн сервере, используем боевой токен
    BOT_TOKEN = '8134901429:AAFlKuE-pnR1Cx5hc-qZCKo55cklv0dyseM'
else:
    # Мы на девелоперской машине, используем тестовый токен
    BOT_TOKEN = '6122819236:AAE-6iJ57CMBsBlJU62gOprmOm_d2ItLIhM'

# Список ID админов бота
ADMIN_IDS = [165879072, 5237388776]