"""Funções auxiliares de formatação e cálculo, usadas pelos comandos."""

from datetime import datetime, timedelta

from config import ALL_RANKS_DISPLAY
from storage import user_daily_time


def format_duration(total_secs):
    hours, remainder = divmod(int(total_secs), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def make_progress_bar(pct, length=12):
    pct = max(0, min(100, pct))
    filled = int(length * pct / 100)
    return "█" * filled + "░" * (length - filled)


def get_rank_info(total_seconds):
    """Retorna (cargo_atual, proximo_cargo) como tuplas (required_time, role_id) ou None."""
    sorted_rewards = sorted(ALL_RANKS_DISPLAY.items())
    current = None
    next_ = None
    for required, role_id in sorted_rewards:
        if total_seconds >= required:
            current = (required, role_id)
        else:
            next_ = (required, role_id)
            break
    return current, next_


def get_last_7_days_total(member_id):
    """Soma o tempo dos últimos 7 dias (incluindo hoje) a partir do histórico diário."""
    if member_id not in user_daily_time:
        return 0

    cutoff = datetime.now().date() - timedelta(days=6)
    total = 0
    for date_str, secs in user_daily_time[member_id].items():
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if d >= cutoff:
                total += secs
        except ValueError:
            continue
    return total
