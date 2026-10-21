"""Formato del archivo: Circ., Secc., Mza. y Parc. No verifica existencia en ARBA."""
import re

CAMPOS_NOMENCLATURA = ("circunscripcion", "seccion", "manzana", "parcela_catastral")


def normalizar_nomenclatura(circunscripcion, seccion, manzana, parcela_catastral):
    valores = [
        str(v or "").strip().upper()
        for v in (circunscripcion, seccion, manzana, parcela_catastral)
    ]
    if any(not v or len(v) > 64 for v in valores):
        raise ValueError("nomenclatura_invalida")
    if not re.fullmatch(r"[0-9]+", valores[0]) or int(valores[0]) == 0:
        raise ValueError("nomenclatura_invalida")
    if not re.fullmatch(r"[A-Z]+", valores[1]):
        raise ValueError("nomenclatura_invalida")
    valores[0] = str(int(valores[0]))
    for i in (2, 3):
        match = re.fullmatch(r"([0-9]+)\s*([A-Z]*)", valores[i])
        if not match or int(match[1]) == 0:
            raise ValueError("nomenclatura_invalida")
        valores[i] = str(int(match[1])) + match[2]
    return dict(zip(CAMPOS_NOMENCLATURA, valores))


def clave_nomenclatura(datos):
    return "-".join(datos[c] for c in CAMPOS_NOMENCLATURA)


def normalizar_busqueda(valor):
    partes = valor.split("-")
    if len(partes) != 4:
        raise ValueError("nomenclatura_invalida")
    return clave_nomenclatura(normalizar_nomenclatura(*partes))

