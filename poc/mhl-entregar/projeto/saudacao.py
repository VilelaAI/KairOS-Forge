def saudar(nome):
    if not nome or not nome.strip():
        raise ValueError("nome não pode ser vazio")
    return f"Bom dia, {nome}!"
