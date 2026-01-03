from config import (CITI_HIGH_THRESHOLD, CITI_LOW_THRESHOLD, COLOR_HIGH,
                    COLOR_LOW, COLOR_MODERATE, EXTRA_WARNING_CT_CITI,
                    RISK_HIGH, RISK_LOW, RISK_MODERATE)


def calculate_citi(
    d_dimer: float, interleukins: float, lymphocytes: float
) -> float:
    """
    Вычисляет CITI-индекс с защитой от деления на ноль.
    """
    denominator = lymphocytes if lymphocytes > 0 else 0.1
    return (d_dimer * interleukins) / denominator


def interpret_citi(citi: float):
    """
    Возвращает уровень риска и цвет по значению CITID.
    """
    if citi < CITI_LOW_THRESHOLD:
        return RISK_LOW, COLOR_LOW
    elif citi <= CITI_HIGH_THRESHOLD:
        return RISK_MODERATE, COLOR_MODERATE
    else:
        return RISK_HIGH, COLOR_HIGH


def get_interpretation_text(citi: float, ct_percent: float) -> str:
    """
    Возвращает полный текст интерпретации, включая дополнительное предупреждение,
    если применимо (CITI > 500_000 и КТ > 70%).
    """
    risk, _ = interpret_citi(citi)
    if citi > CITI_HIGH_THRESHOLD and ct_percent > 70:
        return risk + EXTRA_WARNING_CT_CITI
    return risk
