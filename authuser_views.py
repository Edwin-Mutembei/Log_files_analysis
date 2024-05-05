import pytz
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from api.settings import inProd
from authuser.models import OTP
from authuser.resetPassSerializer import ResetPassSerializer
from authuser.sentOTPSerializer import sentOTPSerializer
from authuser.serializers import AuthUserSerializer
from authuser.validateOTPSerializer import ValidateOTPSerializer
from users.models import CustomUser
from users.serializers import CustomUserSerializer
from utils.ApiResponse import ApiResponse
from utils.Helper import Helper
from utils.Helper2 import Helper2
from django.utils import timezone
from datetime import datetime


class AuthUSer(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = AuthUserSerializer


    def get_serializer_class(self):
        if self.action == 'sendOTP':
            return sentOTPSerializer
        elif self.action == "verifyOTP":
            return ValidateOTPSerializer
        elif self.action == "resetpassword":
            return ResetPassSerializer
        return AuthUserSerializer

    @action(detail=False, methods=['POST'])
    def authUser(self, request):

        username = request.data.get('username')
        password = request.data.get('password')
        otp_method = request.data.get('otp_method', 'email') # Default OTP method is email
        helper = Helper()
        # helper.log(request)
        if username and password:
            try:
                user = CustomUser.objects.get(username=username)
                if user.check_password(password):
                    # if user.check_password(password):
                    if not user.is_verified:
                        response = ApiResponse()
                        response.setStatusCode(status.HTTP_401_UNAUTHORIZED)
                        response.setMessage("Account is not verified")
                        return Response(response.toDict(), status=200)

                    #  Generate OTP and save it
                    otp = helper.generate_otp(self)
                    if otp_method == 'email':
                        identifier = user.email
                    elif otp_method == 'phone_number':
                        identifier = user.phone_number
                    else:
                        identifier = None

                    if identifier:
                        helper.saveotp(self, otp, identifier)

                        # send OTP via chosen method
                        if otp_method == 'email':
                            helper.send_otp_email(self, user.name, otp, user.email)
                            response = ApiResponse()
                            response.setMessage("Check your email for an OTP")
                            response.setStatusCode(status.HTTP_200_OK)
                            return Response(response.toDict(), status=response.status)

                        elif otp_method == 'phone_number':
                            helper.send_otp_sms(self, otp, user.phone_number)
                            response = ApiResponse()
                            response.setMessage("Check your phone for an OTP")
                            response.setStatusCode(status.HTTP_200_OK)
                            return Response(response.toDict(),status = response.status)
                    else:
                        response = ApiResponse()
                        response.setStatusCode(status.HTTP_400_BAD_REQUEST)
                        response.setMessage("Invalid OTP method or Identifier not provided")
                        return Response(response.toDict(), status = response.status)
                else:
                    response = ApiResponse()
                    response.setStatusCode(status.HTTP_400_BAD_REQUEST)
                    response.setMessage("Incorrect login credentials")
                    return Response(response.toDict(), status=200)
            except CustomUser.DoesNotExist:
                response = ApiResponse()
                response.setStatusCode(status.HTTP_400_BAD_REQUEST)
                response.setMessage("Incorrect login credentials")
                return Response(response.toDict(), status=200)
        else:
            response = ApiResponse()
            response.setStatusCode(status.HTTP_400_BAD_REQUEST)
            response.setMessage("Username and password are required")
            return Response(response.toDict(), status=response.status)


    # @action(detail=False, methods=['POST'])
    # def sendOTP(self, request):
    #     response = ApiResponse()
    #     helper = Helper()
    #     # helper.log(request)
    #     serializer = sentOTPSerializer(data=request.data)
    #     if serializer.is_valid():
    #         email = serializer.validated_data.get('email')
    #         phone_number = serializer.validated_data.get('phone_number')
    #         print(email)
    #         print(phone_number)
    #         if email:
    #             identifier = email
    #
    #         elif phone_number:
    #             identifier = phone_number
    #
    #         else:
    #             response.setStatusCode((status.HTTP_400_BAD_REQUEST))
    #             response.setMessage('Either email or phone number must be provided')
    #             return  Response(response.toDict(), status=status.HTTP_400_BAD_REQUEST)
    #
    #         try:
    #             #Try to find the user by either email or phone number
    #             user = CustomUser.objects.get(email = email) if email else CustomUser.objects.get(phone_number=phone_number)
    #             user_serializer = CustomUserSerializer(user)
    #             name = user_serializer.data.get('name')
    #
    #             # Generate and save OTP
    #             otp = helper.generateotp()
    #             save_otp = helper.saveotp(self, otp, identifier)
    #
    #             # Send OTP to either email or phone number
    #             if email:
    #                 sent =helper.send_otp_email(self, name, otp, email)
    #             else:
    #                 sent = helper.send_otp_sms(self, otp, phone_number)
    #
    #             if sent == 1:
    #                 print("Sent OTP: ", otp)
    #                 response.setMessage("An OTP was sent to your Email/phone number.")
    #                 response.setStatusCode(200)
    #                 return Response(response.toDict(), 200)
    #
    #             else:
    #                 response.setMessage("Failed to send Email/SMS")
    #                 response.setStatusCode(401)
    #                 return Response(response.toDict(), 200)
    #
    #
    #
    #         except CustomUser.DoesNotExist:
    #             response.setMessage("No record found with this Email/phone number")
    #             response.setStatusCode(404)
    #             return Response(response.toDict(), status = response.status)
    #
    #     else:
    #         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




    @action(detail=False, methods=['POST'])
    def verifyOTP(self, request):
        response = ApiResponse()
        serializer = ValidateOTPSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.validated_data.get('otp')
            identifier = serializer.validated_data.get('identifier')

            try:
                existing_otp = OTP.objects.filter(identifier= identifier).last()
                if existing_otp.otp == otp:
                    current_time = timezone.now()
                    expirydate_str_without_timezone = existing_otp.expirydate.rsplit('.', 1)[0]
                    expiry_time = datetime.strptime(expirydate_str_without_timezone, "%Y-%m-%d %H:%M:%S")
                    # expiry_time = timezone.make_aware(expiry_time, timezone.utc)
                    expiry_time = pytz.utc.localize(expiry_time)
                    if current_time <= expiry_time:
                        response.setMessage("OTP validated")
                        response.setStatusCode(200)
                        return Response(response.toDict(), 200)
                    else:
                        response.setMessage("OTP has expired")
                        response.setStatusCode(400)
                        return Response(response.toDict(), 200)
                else:
                    response.setMessage("Invalid OTP")
                    response.setStatusCode(400)
                    return Response(response.toDict(), 200)
            except OTP.DoesNotExist:
                response.setMessage("OTP does not exist for the provided email/phone number")
                response.setStatusCode(404)
                return Response(response.toDict(), 200)

        response.setMessage("Invalid data provided")
        response.setStatusCode(400)
        return Response(response.toDict(), 200)

    @action(detail=False, methods=['POST'])
    def resetpassword(self, request):
        response = ApiResponse()
        helper2 = Helper2()
        # helper2.log(request)
        serializer = ResetPassSerializer(data=request.data)
        if serializer.is_valid():
            # password = serializer.validated_data.get('password')
            resetpassword = serializer.validated_data.get('resetpassword')
            email = serializer.validated_data.get('email')
            if email:
                try:
                    user = CustomUser.objects.get(email=email)
                    user_serializer = CustomUserSerializer(user)
                    name = user_serializer.data.get('name')
                    resetpassword = helper2.generateresetpassword()
                    try:
                        user.set_password(resetpassword)
                        user.save()
                        sent = helper2.resetpassword(name, resetpassword, email)
                        if sent == 1:
                            print('Sent resetpassword: ', resetpassword)
                            response.setMessage('A new password was sent to your email.')
                            response.setStatusCode(200)
                            return Response(response.toDict(),200)
                        else:
                            response.setMessage('Failed to send email')
                            response.setStatusCode(401)
                            return Response(response.toDict(),200)

                    except Exception as e:
                        response.setMessage(f'Error sending email: {str(e)}')
                        response.setStatusCode(401)
                        return Response(response.toDict(),200)



                except CustomUser.DoesNotExist:
                    response.setMessage('User not found')
                    response.setStatusCode(404)
                    return Response(response.toDict(), 200)

            else:
                status_code = status.HTTP_400_BAD_REQUEST
                return Response({'message': 'Email parameter is recquired', 'status': status_code})

        else:
            return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)



