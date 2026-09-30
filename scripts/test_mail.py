#!/usr/bin/env python3
"""Prueba la configuracion SMTP de config/.env enviando un mail de prueba.

Corre en un proceso aparte: sirve para validar credenciales ANTES de reiniciar
el servicio (las variables de entorno se leen al arrancar). Nunca imprime la
contrasena.

Uso:
    venv/bin/python3 scripts/test_mail.py                      # solo verifica login
    venv/bin/python3 scripts/test_mail.py destino@mail.com     # ademas envia
"""
import os
import ssl
import sys
import smtplib
import socket
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE, 'config/.env'))


def main():
    host = os.getenv('MAIL_SMTP_HOST', '')
    port = int(os.getenv('MAIL_SMTP_PORT', '465'))
    user = os.getenv('MAIL_SMTP_USER', '')
    pwd = os.getenv('MAIL_SMTP_PASS', '')
    sender = os.getenv('MAIL_FROM', user)
    vendedor = os.getenv('MAIL_VENDEDOR', '')
    destino = sys.argv[1] if len(sys.argv) > 1 else None

    print('CONFIGURACION LEIDA DE config/.env')
    print('-' * 52)
    print(f'  MAIL_SMTP_HOST : {host}')
    print(f'  MAIL_SMTP_PORT : {port}')
    print(f'  MAIL_SMTP_USER : {user}')
    print(f'  MAIL_SMTP_PASS : {"*" * 8} ({len(pwd)} caracteres)')
    print(f'  MAIL_FROM      : {sender}')
    print(f'  MAIL_VENDEDOR  : {vendedor}')
    if not (host and user and pwd):
        print('\nFALTAN DATOS: revisa config/.env')
        return 1

    print(f'\n1) Resolviendo {host} ...')
    try:
        ip = socket.gethostbyname(host)
        print(f'   OK -> {ip}')
    except Exception as e:
        print(f'   ERROR de DNS: {e}')
        return 1

    print(f'2) Conectando por SSL a {host}:{port} ...')
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=25) as s:
            print('   conexion OK')
            print('3) Autenticando ...')
            s.login(user, pwd)
            print('   LOGIN OK — las credenciales son correctas')

            if destino:
                print(f'4) Enviando mail de prueba a {destino} ...')
                ahora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f'Prueba SMTP Mercadomuebles — {ahora}'
                msg['From'] = sender
                msg['To'] = destino
                cuerpo = (
                    f'Mail de prueba del sistema Cannon.\n\n'
                    f'Servidor : {host}:{port} (SSL)\n'
                    f'Usuario  : {user}\n'
                    f'Remitente: {sender}\n'
                    f'Fecha    : {ahora}\n\n'
                    f'Si estas leyendo esto, la configuracion SMTP nueva funciona.\n'
                )
                msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
                s.sendmail(sender, [destino], msg.as_string())
                print('   ENVIADO OK')
            else:
                print('   (sin destino: no se envio nada)')
    except smtplib.SMTPAuthenticationError as e:
        print(f'   ERROR DE AUTENTICACION: usuario o contrasena incorrectos')
        print(f'   detalle: {e}')
        return 1
    except Exception as e:
        print(f'   ERROR: {type(e).__name__}: {e}')
        return 1

    print('\nTODO OK. El cambio ya se puede aplicar reiniciando el servicio.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
