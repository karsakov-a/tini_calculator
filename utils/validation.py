def create_float_regex(
    max_integer_digits: int, max_decimal_digits: int = 5
) -> str:
    """Генерирует регулярное выражение для чисел с плавающей точкой."""
    int_part = f"\\d{{1,{max_integer_digits}}}"
    dec_part = f"\\.\\d{{1,{max_decimal_digits}}}"
    return f"^({int_part}{dec_part}?|{dec_part})$"
