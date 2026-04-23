import tokenize
import io

def remove_comments(source_code):
    io_obj = io.StringIO(source_code)
    out = ""
    last_lineno = -1
    last_col = 0
    for tok in tokenize.generate_tokens(io_obj.readline):
        token_type = tok[0]
        token_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out += (" " * (start_col - last_col))
        if token_type == tokenize.COMMENT:
            pass
        else:
            out += token_string
        last_lineno = end_line
        last_col = end_col
    return out

files = [
    r"c:\Users\DELL\Desktop\UABC\4to Semestre\Estructura de Datos\Genetic-Programming\Prueba FastAPI.py",
    r"c:\Users\DELL\Desktop\UABC\4to Semestre\Estructura de Datos\Genetic-Programming\Práctica GP.py"
]

for f in files:
    with open(f, "r", encoding="utf-8") as file:
        text = file.read()
    with open(f, "w", encoding="utf-8") as file:
        file.write(remove_comments(text))
    print(f"Comments removed from {f}")
