import time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from utils.connect import SSHCommandExecutor
from utils.Helper import Helper
from utils.ApiResponse import ApiResponse
from rest_framework import viewsets

class CommandExecutionView(viewsets.ModelViewSet):

    def monitor_service(self, executor):
        # Set a default command to execute (if needed)

        try:
            command_to_execute = "cfg; ls"
            stdout,stderr = executor.execute_command(command_to_execute)
            output = stdout
            print(output)
            lines =  output.strip().splitlines('\n')

            #parse the output into a list of dictionaries
            service = []
            for line in lines:
                # Split line by whitespace
                parts = line.split()
                if len(parts) >= 2:
                    service_name, status = parts[0], parts[1]
                    if 'cfg' in service_name.lower():
                        service.append({'service_name': service_name, 'status': status})

            return {'status': 'success', 'services': service}

        except Exception as e:
            print('Error: ', str(e))
            return []

    def connect_to_server(self):
        try:
            # Replace these values with your server's details
            hostname = '3.130.157.173'
            username = 'ec2-user'
            private_key_path = 'files/serverkey'

            # Create an instance of SSHCommandExecutor
            executor = SSHCommandExecutor(hostname, username, private_key_path)
            print('Connected to the server successfully')
            return executor


        except Exception as e:
            # Handle any exceptions
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def read_service(self, request, *args, **kwargs):
        try:
            executor = self.connect_to_server()

            # Monitor services
            if executor:
                json_data = self.monitor_service(executor)
                response = ApiResponse()
                response.setMessage("Service retrieved")
                response.setEntity(json_data)
                response.setStatusCode(200)

                # Close the SSH connection
                executor.disconnect()
                print("SSH connection closed.")
                return Response(response.toDict(), 200)
        except Exception as e:
            # Handle exceptions during execution
            print('Error in read_service:', str(e))
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



