import base64
import os
import pickle
from email.mime.text import MIMEText

from fastapi import FastAPI, HTTPException
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_DIR = os.path.join(os.path.dirname(__file__), "credentials")
CLIENT_SECRET_FILE = os.path.join(CREDENTIALS_DIR, "credentials.json")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "token.pickle")

app = FastAPI(title="Servicio de notificaciones")


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


def create_message(to: str, subject: str, html_content: str) -> dict[str, str]:
    message = MIMEText(html_content, "html", "utf-8")
    message["to"] = to
    message["subject"] = subject
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
