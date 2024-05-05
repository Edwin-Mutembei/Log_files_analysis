import os
import random
import paramiko
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from api import settings
from authuser.models import OTP
from datetime import timedelta, datetime
from servers.models import ServerConfiguration
from api.settings import BASE_DIR, FILE_URL
from utils.ApiResponse import ApiResponse


from api.settings import *
import africastalking


class Helper:
    africastalking.initialize(
        username= settings.AFRICAS_TALKING_USERNAME,
        api_key= settings.AFRICAS_TALKING_API_KEY,
    )
    sms = africastalking.SMS


    @staticmethod
    def send_otp_email(self, name, otp, email):
        try:
            email_content = f"""
            <html>
                <head>
                    <style>
                        font-size: 12px;
                    </style>
                </head>
                <body>
                    <p>Hello {name},</p>
                    <p tyle="font-size: 20px, color: black;">Use: <span class="otp" >{otp}</span></p>
                    <p>If you did not request this, please ignore. Do not share OTP with anyone.</p>
                </body>
            </html>
            """
            sent = send_mail(
                'Verification OTP',
                '',
                'no-reply@gmail.com',
                [email],
                fail_silently=False,
                html_message=email_content,
            )
            return sent

        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return 0

    @staticmethod
    def send_otp_sms(self, otp, phone_number):
        sms = africastalking.SMS
        otp_message = f'Your OTP code is {otp}. Please do not share this code with anyone'
        try:
            response = sms.send(otp_message, [phone_number])
            return response         #return Africa's talking SMS response
        except Exception as e:
            print(f'Error sending SMS: {str(e)}')
            return None         # indicate failure to send sms

    @staticmethod
    def generate_otp(self):
        characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz"
        otp = ''.join(random.choice(characters) for _ in range(8))
        return otp

    @staticmethod
    def saveotp(self, otp, identifier):
        expiry_time = timezone.now() + timedelta(minutes=5)
        otp_data = OTP(
            otp=otp,
            identifier = identifier,  # This is either email or phone number
            expirydate=expiry_time,
            phone_number = identifier,
            email = identifier
        )
        otp_data.save()

    @staticmethod
    def log(request):
        current_date = datetime.now().strftime('%Y.%m.%d')
        log_file_name = f"{current_date}-request.log"
        log_file_path = os.path.join(BASE_DIR, f'utils/logs/{log_file_name}')
        log_string = f"[{datetime.now().strftime('%Y.%m.%d %I.%M.%S %p')}] => method: {request.method} uri: {request.path} queryString: {request.GET.urlencode()} protocol: {request.scheme} remoteAddr: {request.META.get('REMOTE_ADDR')} remotePort: {request.META.get('REMOTE_PORT')} userAgent: {request.META.get('HTTP_USER_AGENT')}"
        mode = 'a' if os.path.exists(log_file_path) else 'w'
        with open(log_file_path, mode) as log_file:
            log_file.write(log_string + '\n')

    @staticmethod
    def connect_to_server(ip_address):
        response =ApiResponse()
        try:
            server = ServerConfiguration.objects.get(ip_address=ip_address)

            if server.connType == 'password':
                return Helper.connect_with_password(server.ip_address, server.username, server.password)
            else:

                if not os.path.exists(f'{FILE_URL}{server.filename}'):
                    response.setMessage("Server key is not found")
                    response.setStatusCode(404)
                    response.setEntity()
                    return Response(response.toDict(), 200)

                return Helper.connect_with_key(server.ip_address, server.username, f'{FILE_URL}{server.filename}')
        except ServerConfiguration.DoesNotExist:
            print("Server configuration not found for IP address:", ip_address)
            return None



    @staticmethod
    def connect_with_password(hostname, username, password):
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh_client.connect(hostname=hostname, port=22, username=username, password=password)
            print("Connected to server successfully!")
            return ssh_client
        except paramiko.AuthenticationException:
            print("Authentication failed, please check your credentials.")
            return None
        except paramiko.SSHException as e:
            print("Unable to establish SSH connection:", str(e))
            return None
        except Exception as e:
            print("Error:", str(e))
            return None

    @staticmethod
    def connect_with_key(hostname, username, filename):
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(hostname=hostname, port=22, username=username, key_filename=filename)
            print("Connected to server successfully!")
            return ssh_client
        except paramiko.AuthenticationException:
            print("Authentication failed. Please check your private key and username.")
            return None
        except paramiko.SSHException as e:
            print("SSH connection failed:", str(e))

            return None
        except Exception as e:
            print("Error:", str(e))
            return None





