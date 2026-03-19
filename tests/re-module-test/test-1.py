import re

print(re.findall(r"\d+", "Order ID: 12345"))

print(re.findall(r"\d+", "a1 b22 c333"))

print(re.findall(r"^\d+", "123abc"))

print(re.findall(r"\d", "ID: 123"))

print(re.findall(r"\d{2}", "ID: 123"))
print(re.findall(r"\d{2}", "ID: 1234"))

print(re.findall(rf"\d{2}", "ID: 123"))

print(re.findall(r": \d{1}", "ID: 123"))
print(re.findall(r": (\d{1})", "ID: 123"))

print(re.findall(r"(\d{1})", "ID: 1234"))
print(re.findall(r"(\d{1}){1}", "ID: 1234"))

print(re.findall(r"(\d{1}){2}", "ID: 1234"))
print(re.findall(r"(\d{1})(\d{1})", "ID: 1234"))