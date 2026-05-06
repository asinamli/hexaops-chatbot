def add_numbers(a, b) -> int:
    a = int(a)
    b = int(b)
    return a + b


def subtract_numbers(a, b) -> int:
    a = int(a)
    b = int(b)
    return a - b


def multiply_numbers(a, b) -> int:
    a = int(a)
    b = int(b)
    return a * b


def divide_numbers(a, b):
    a = int(a)
    b = int(b)

    if b == 0:
        raise ValueError("Bir sayı sıfıra bölünemez.")

    return a / b