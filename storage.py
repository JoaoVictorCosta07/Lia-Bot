"""Persistência em disco (JSON) e estado em memória compartilhado entre os cogs.

Os dicionários abaixo são importados por outros módulos via
`from storage import user_total_time` etc. Como dicionários são mutáveis,
todos os módulos enxergam as mesmas instâncias — por isso load_data() e
load_daily_data() usam .clear()/.update() em vez de reatribuir a variável,
o que quebraria essas referências.
"""

import json
import os
from datetime import datetime

from config import DAILY_DATA_FILE, DATA_FILE

# Timestamp de início da sessão atual de cada usuário em call: {member_id: timestamp}
user_voice_times = {}

# Tempo total acumulado (all-time) em segundos: {member_id: total_seconds}
user_total_time = {}

# Tempo por dia, pra calcular "últimos 7 dias": {member_id: {"YYYY-MM-DD": seconds}}
user_daily_time = {}


def load_data():
    """Carrega o tempo total acumulado do arquivo JSON."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            user_total_time.clear()
            user_total_time.update({int(k): v for k, v in raw.items()})
            print(f"Dados totais carregados: {len(user_total_time)} usuário(s).")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Erro ao carregar {DATA_FILE}: {e}. Iniciando com dados vazios.")
    else:
        print("Nenhum arquivo de dados totais encontrado. Iniciando do zero.")


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in user_total_time.items()}, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar {DATA_FILE}: {e}")


def load_daily_data():
    """Carrega o histórico diário do arquivo JSON."""
    if os.path.exists(DAILY_DATA_FILE):
        try:
            with open(DAILY_DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            user_daily_time.clear()
            user_daily_time.update({int(k): v for k, v in raw.items()})
            print(f"Dados diários carregados: {len(user_daily_time)} usuário(s).")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Erro ao carregar {DAILY_DATA_FILE}: {e}. Iniciando com dados vazios.")
    else:
        print("Nenhum arquivo de dados diários encontrado. Iniciando do zero.")


def save_daily_data():
    try:
        with open(DAILY_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in user_daily_time.items()}, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar {DAILY_DATA_FILE}: {e}")


def add_time(member_id, duration):
    """Soma 'duration' segundos ao total e ao dia de hoje do usuário."""
    if duration <= 0:
        return

    user_total_time[member_id] = user_total_time.get(member_id, 0) + duration

    today_str = datetime.now().strftime("%Y-%m-%d")
    user_daily_time.setdefault(member_id, {})
    user_daily_time[member_id][today_str] = user_daily_time[member_id].get(today_str, 0) + duration
