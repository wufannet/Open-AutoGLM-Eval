def _convert_relative_to_absolute(element: list[int], screen_width: int, screen_height: int
) -> tuple[int, int]:
    """Convert relative coordinates (0-1000) to absolute pixels."""
    x = int(element[0] / 1000 * screen_width)
    y = int(element[1] / 1000 * screen_height)
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
# element = [
#       395,
#       568
#     ]
element = [
      395,
      592
    ]
element2 = [
      395,
      654
    ]

#       653
x, y = _convert_relative_to_absolute(element, 720, 1560)
print(x, y)
print(f"adb -s MQS0219610003655 shell tap {x} {y}")

x, y = _convert_relative_to_absolute(element2, 720, 1560)
print(x, y)
print(f"adb -s MQS0219610003655 shell tap {x} {y}")

