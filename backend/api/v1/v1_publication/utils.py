from .constants import DroughtCategory


def get_category(value: float):
    value = round(value, 3)
    if (value < 0):
        return DroughtCategory.none
    if (value >= 0 and value <= 2):
        return DroughtCategory.d4
    if (value > 2 and value <= 5):
        return DroughtCategory.d3
    if (value > 5 and value <= 10):
        return DroughtCategory.d2
    if (value > 10 and value <= 20):
        return DroughtCategory.d1
    if (value > 20 and value <= 30):
        return DroughtCategory.d0
    return DroughtCategory.normal
