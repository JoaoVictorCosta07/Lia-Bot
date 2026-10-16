"""Configurações e constantes do bot."""

# Cargo inicial, atribuído manualmente via !recrutar
RECRUTA_ROLE_ID = 1552057504601608313

# Canais de voz que não contam tempo (ex: AFK)
IGNORED_VOICE_CHANNELS = {
    1552060896770134106,
}

# Canal onde são anunciadas novas conquistas de cargo
ANNOUNCE_CHANNEL_ID = 1552060059813421187

# Canal onde são publicados os avisos de punição
PUNISHMENT_CHANNEL_ID = 1556144583669186602

"""
🪖 Recruta — 0h
🎖️ Soldado — 3h
🎖️ Cabo — 10h
🎖️ 3º Sargento — 20h
🎖️ 2º Sargento — 35h
🎖️ 1º Sargento — 50h
🏅 Subtenente — 75h
⭐ Aspirante — 100h
⭐ Tenente — 150h
🦅 Capitão — 200h
🦅 Major — 300h
🏆 Coronel — 450h
🏆 Veterano Expedicionário — 600h
"""

ROLE_REWARDS = {
    10800: 1552058050796458045,   # soldado
    36000: 1552058132321271909,   # cabo
    72000: 1552058207155789905,   # 3º sargento
    126000: 1552058275644710922,  # 2º sargento
    180000: 1552058333920235552,  # 1º sargento
    270000: 1552058311090896916,  # subtenente
    360000: 1552058326173487135,  # aspirante
    540000: 1552058340270407730,  # tenente
    720000: 1552058632982630424,  # capitão
    1080000: 1552058625986527252, # major
    1620000: 1552058803300732948, # coronel
    2160000: 1552058795335884912, # veterano expedicionário
}

# Versão para exibição no !tempo, incluindo o Recruta como patamar inicial (0h)
ALL_RANKS_DISPLAY = {0: RECRUTA_ROLE_ID, **ROLE_REWARDS}

# Arquivos de persistência
DATA_FILE = "voice_times.json"
DAILY_DATA_FILE = "voice_daily.json"

# Intervalo (em segundos) do loop que verifica sessões de voz em andamento
# Suba para 60+ em produção, já que os limiares reais estão em horas
CHECK_INTERVAL_SECONDS = 5
