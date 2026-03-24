def _convert_relative_to_absolute(element: list[int], screen_width: int, screen_height: int
) -> tuple[int, int]:
    """Convert relative coordinates (0-1000) to absolute pixels."""
    x = int(element[0] / 1000 * screen_width)
    y = int(element[1] / 1000 * screen_height)
    return x, y

def _convert_abs_to_rel(element: list[int], screen_width: int, screen_height: int
) -> tuple[int, int]:
    """Convert relative coordinates (0-1000) to absolute pixels."""
    x = int(element[0] * 1000 / screen_width)
    y = int(element[1] * 1000 / screen_height)
    return x, y

#实现
def _convert_abs_to_rel_more(element: list[int], screen_width: int, screen_height: int
) -> tuple[int, int]:

    return x, y

"""Handle tap action."""
# {
#   "_metadata": "do",
#   "action": "Tap",
#   "element": [
#     756,
#     946
#   ]
# }
element = [
      395,
      922
    ]
element2 = [
      395,
      1019
    ]

x, y = _convert_abs_to_rel(element, 720, 1560)
print(f"_convert_abs_to_rel {x} {y}")

x, y = _convert_abs_to_rel(element2, 720, 1560)
print(f"_convert_abs_to_rel {x} {y}")




