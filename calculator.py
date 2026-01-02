def calculate_citi(
    d_dimer: float, interleukins: float, lymphocytes: float
) -> float:
    """
    Вычисляет CITI-индекс по формуле:
        CITI
          = (Д-димер × Интерлейкины) / (Лимфоциты + 0.1)
    Защита от деления на ноль: если лимфоциты == 0 → используется 0.1
    """
    denominator = lymphocytes if lymphocytes > 0 else 0.1
    return (d_dimer * interleukins) / denominator
    # return (d_dimer * interleukins) / (denominator + 0.1)


def interpret_citi(citi: float):
    """
    Возвращает уровень риска и цветовую метку.
    Returns:
        tuple: (risk_level: str, color: str)
    """
    if citi < 100_000:
        return "Низкий риск смерти", "#4CAF50"  # Зелёный
    elif citi <= 500_000:
        return "Умеренный риск", "#FFC107"  # Жёлтый
    else:
        return "Высокий риск смерти", "#F44336"  # Красный
