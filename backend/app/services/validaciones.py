"""Reglas de validación compartidas: contraseñas y cédula ecuatoriana."""
from fastapi import HTTPException


def validar_password(password: str) -> None:
    """Mínimo 8 caracteres, con al menos una letra y un número."""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres.")
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos una letra y un número.")


def cedula_valida(cedula: str) -> bool:
    """
    Cédula ecuatoriana de 10 dígitos: provincia 01-24 (o 30 para ecuatorianos en el exterior),
    tercer dígito menor que 6 y dígito verificador por módulo 10.
    """
    if len(cedula) != 10 or not cedula.isdigit():
        return False
    provincia = int(cedula[:2])
    if not (1 <= provincia <= 24 or provincia == 30):
        return False
    if int(cedula[2]) >= 6:
        return False
    suma = 0
    for i, ch in enumerate(cedula[:9]):
        valor = int(ch) * (2 if i % 2 == 0 else 1)
        suma += valor - 9 if valor > 9 else valor
    verificador = (10 - suma % 10) % 10
    return verificador == int(cedula[9])


def validar_cedula(cedula: str) -> str:
    cedula = (cedula or "").strip()
    if not cedula_valida(cedula):
        raise HTTPException(status_code=400, detail="La cédula no es válida. Revise los 10 dígitos.")
    return cedula
