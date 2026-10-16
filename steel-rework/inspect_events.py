from archive import *
b=(SRC/'Event.pak').read_bytes()
for e in entries(b):print(e)
