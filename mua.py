from colour import RGB_to_HSV, HSV_to_RGB
from colour.algebra import normalise_maximum
import numpy as np

def complementary_color(rgb):
    """Вычисляет комплементарный цвет через HSV пространство"""
    hsv = RGB_to_HSV(rgb)
    hsv[0] = (hsv[0] + 0.5) % 1.0  
    return HSV_to_RGB(hsv)

