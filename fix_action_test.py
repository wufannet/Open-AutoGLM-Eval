response ='do(action=Tap element=[499, 938])'
print(f"Parsing action: {response}")
response = response.replace("Tap element", '"Tap", element').strip()
print(f"replace action: {response}")