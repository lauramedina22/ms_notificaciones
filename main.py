import base64
import os
import pickle
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import FastAPI, HTTPException
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
BASE_DIR = os.path.dirname(__file__)
CREDENTIALS_DIR = os.path.join(BASE_DIR, "credentials")
CLIENT_SECRET_FILE = os.path.join(CREDENTIALS_DIR, "credentials.json")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "token.pickle")
LOGO_PATH = os.path.join(BASE_DIR, "JPASports.jpg")

app = FastAPI(title="Servicio de notificaciones - JPA Sports")


class EmailRequest(BaseModel):
    to: str = Field(min_length=1, description="Dirección de correo destinataria")
    subject: str = Field(min_length=1, description="Asunto del correo")
    html_content: str = Field(min_length=1, description="Contenido HTML del correo")


def authenticate_gmail():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return creds


def build_corporate_template(subject: str, content: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
        <style>
            .rounded-circle {{
                border-radius: 50% !important;
                overflow: hidden;
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f2; color: #333333;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f4f7f2; padding: 30px 15px;">
            <tr>
                <td align="center">
                    <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);">
                        <!-- Cabecera Corporativa -->
                        <tr>
                            <td align="center" style="background: linear-gradient(to right, #70B038 0%, #cbe5b3 30%, #eff8e8 60%, #ffffff 100%); z-index: 0; padding: 32px 24px; border-bottom: 1px solid #e2efd9;">
                                <img src="cid:logo_jpasports" alt="JPA Sports Logo" class="rounded-circle" width="120" height="120" style="display: block; border-radius: 50%; object-fit: cover; box-shadow: 0 4px 12px rgba(0,0,0,0.12);">
                                <h1 style="margin: 16px 0 4px 0; color: #2d4c14; font-size: 26px; font-weight: 700; letter-spacing: 0.5px;">¡Bienvenido a JPA Sports!</h1>
                                <p style="margin: 0; color: #4a6b2f; font-size: 15px; font-weight: 500;">Tu pasión por el deporte, en el mejor lugar</p>
                            </td>
                        </tr>

                        <!-- Mensaje de Bienvenida y Contenido -->
                        <tr>
                            <td style="padding: 32px 36px;">
                                <p style="margin: 0 0 18px 0; font-size: 16px; line-height: 1.6; color: #4a5568;">
                                    ¡Hola! Nos alegra muchísimo tenerte con nosotros en la comunidad de <strong style="color: #70B038;">JPA Sports</strong>. A continuación, te compartimos los detalles de tu notificación:
                                </p>

                                <!-- Caja destacada con el contenido dinámico -->
                                <div style="background-color: #f8fbf6; border-left: 5px solid #70B038; border-radius: 8px; padding: 20px 24px; margin: 24px 0; font-size: 16px; line-height: 1.6; color: #2d3748;">
                                    {content}
                                </div>

                                <p style="margin: 24px 0 0 0; font-size: 15px; line-height: 1.6; color: #4a5568;">
                                    Si tienes alguna duda o necesitas asistencia, nuestro equipo está siempre listo para ayudarte en la cancha.
                                </p>
                            </td>
                        </tr>

                        <!-- Pie de página -->
                        <tr>
                            <td align="center" style="background: linear-gradient(to right, #70B038 0%, #cbe5b3 30%, #eff8e8 60%, #ffffff 100%); z-index: 0; padding: 24px 30px; color: #2d4c14; font-size: 13px; line-height: 1.5; border-top: 1px solid #e2efd9;">
                                <p style="margin: 0 0 6px 0; font-weight: 700; color: #1e350d; font-size: 14px;">JPA Sports</p>
                                <p style="margin: 0; color: #3b5a22;">Este es un mensaje automático generado por el sistema de notificaciones.</p>
                                <p style="margin: 8px 0 0 0; font-size: 12px; color: #527536;">© 2026 JPA Sports. Todos los derechos reservados.</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def create_message(to: str, subject: str, html_content: str) -> dict[str, str]:
    message = MIMEMultipart("related")
    message["to"] = to
    message["subject"] = subject

    styled_html = build_corporate_template(subject, html_content)

    msg_alternative = MIMEMultipart("alternative")
    message.attach(msg_alternative)
    msg_alternative.attach(MIMEText(styled_html, "html", "utf-8"))

    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as img_file:
            img_data = img_file.read()
        mime_img = MIMEImage(img_data)
        mime_img.add_header("Content-ID", "<logo_jpasports>")
        mime_img.add_header("Content-Disposition", "inline", filename="JPASports.jpg")
        message.attach(mime_img)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw_message}


@app.post("/send-email")
def send_email(email: EmailRequest) -> dict[str, str]:
    try:
        credentials = authenticate_gmail()
        service = build("gmail", "v1", credentials=credentials)
        sent_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message(email.to, email.subject, email.html_content))
            .execute()
        )
    except HttpError as error:
        raise HTTPException(
            status_code=502, detail=f"Error al enviar el correo con Gmail: {error}"
        ) from error

    return {"message": "Correo enviado", "id": sent_message["id"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
