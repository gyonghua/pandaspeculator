import alerts.alerts_config as alerts_config
from alerts.telegram_bots import Bar_pattern_bot


Alert = Bar_pattern_bot(alerts_config.telegramApi, "H1")

Alert.notify_patterns()
