import os
# from flask_socketio import SocketIO
import json
import os
import cv2
import imutils
import pickle
import socket
import datetime
import time
import auxiliary_functions

BUFF_SIZE = 65536
HEADERSIZE = 10

class ModelSocket:
    
    def __init__(self, video_name):
        self.video_name = video_name

        from Rescue_Sign import RescueSignModel
        self.model = RescueSignModel()

    def get_src_vid_path(self):
        self.file_path = os.path.abspath(__file__)

        # Get the directory name of the current file
        self.dir_name = os.path.dirname(self.file_path)

        # For ubuntu:
        # self.videos_location = f'{self.dir_name}/static'
        # self.path_out = f'{self.dir_name}/static/model-server-frames'

        # For windows:
        self.videos_location = self.dir_name + '\static'
        self.path_out = self.dir_name + '\static\model-server-frames'


        return self.path_out, self.videos_location

    def open_operator_socket(self):
        print("::: open_operator_socket() ::::")
        import requests
        url = "http://127.0.0.1:5050/create_socket_connection"

        headers = {
            'Content-Type': 'application/json'
        }

        # Send a GET request:
        response = requests.get(url, headers=headers)

        # Check the response status code
        if response.status_code == 200:  # 200 indicates a successful request
            # Access the response content
            data = response.json()  # Assuming the response is in JSON format
            # Process the data or perform further operations
            print(data)
        else:
            print("GET request failed with status code:", response.status_code)

    def create_socket_and_bind_it(self):
        HOST = '127.0.0.1'  #  the server will listen for connections on the same machine.
        PORT = 4001  # The port number 4001 is assigned to the server.

        # self.open_operator_socket()

        # socket.socket() - A socket object is created.
        # socket.AF_INET - specifying the address family as AF_INET (IPv4)
        # socket.SOCK_DGRAM - specifying the socket type as SOCK_DGRAM (UDP socket)
        self.model_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        
        #  setsockopt() - set the socket's receive buffer size.
        # SOL_SOCKET (socket-level option)
        # SO_RCVBUF (receive buffer size).
        self.model_server_socket.setsockopt(
        socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)

        # Bind the socket to a specific address and port
        socket_address = (HOST, PORT)
        self.model_server_socket.bind(socket_address)

        print(f"Listening at: {socket_address}")
        print('Waiting for operator server connection...')

        msg, self.client_addr = self.model_server_socket.recvfrom(BUFF_SIZE)

        # Receive data from the operator server
        # print('Data received from Operator server: ', msg.decode())

        # return model_server_socket, client_addr

    def send_frames_by_chunks(self):
        print(":: send_frames_by_chunks ::")
        # Get the full path of the current file
        _, static_folder_location = self.get_src_vid_path()
        pendingImages_folder = 'C:\\Users\\project25\\RescueSign\\PendingImages'

        video_src = static_folder_location + "\\" + self.video_name
        print(f"video_src = {video_src}")

        # Open the video file or capture from a camera
        vid = cv2.VideoCapture(video_src)

        
        # initialize frame_counter:
        frames_counter = 0
        total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
        vid_frame_rate = vid.get(cv2.CAP_PROP_FPS)
        current_frame = 0
        frame_chunk_size = 100
        frames_chunk = []
        frame_index = 0

        print(f"total frames = {total_frames}")
        time1 = time.time()
        
        # Choose frame rate 
        fps = 6  # Desired frame rate (4 frames per second)

        while vid.isOpened():
            return_val, frame = vid.read()
            if not return_val:
            
                # If there are frames that have not yet been sent:
                if len(frames_chunk) > 0:
                    # print("::: if len(frames_chunk) > 0::::")
                    try:
                        print(" :: Run the model ::")
                        self.model.run_model()
                        print(f":::: model.output :::")
                        print(self.model.output)  

                        # If the model found positive images
                        if len(self.model.output) > 0:
                            print(f"::::create socket and bind it with the operator :::")
                            self.create_socket_and_bind_it()

                            print(":: send_frames_to_operator ::")
                            self.send_frames_to_operator(frames_chunk, self.model.output)
                    except Exception as e:
                        print("An exception occured: ", str(e))
                
                break

            # Calculate the elapsed time since the last frame
            # elapsed_time = time.time() - start_time

            frame_position = vid.get(cv2.CAP_PROP_POS_FRAMES)
            # print("--------------------------------------------")
            
            import math
            if (frame_position % math.ceil(vid_frame_rate/fps) == 0):
                # print(f":::::: frame_index = {frame_index}")
                frame_and_id = self.save_frame_on_disk(frame, pendingImages_folder)
                # print(f"frame_and_id[1] = {frame_and_id[1]}")

                frames_chunk.append(frame_and_id)
                # print(f":::: frames_counter = {frames_counter}")
                frames_counter +=1

            # current_frame +=1

            
            # print(f":::: frame_chunk_size = {frame_chunk_size}")
            # print(f":::: len(frames_chunk) = {len(frames_chunk)}")
            if frames_counter >= frame_chunk_size:
                try:
                    self.model.run_model()
                    print(f":::: model.output :::")
                    print(self.model.output)  

                    if len(self.model.output) > 0:
                        self.create_socket_and_bind_it()
                        self.send_frames_to_operator(frames_chunk, self.model.output)
                except Exception as e:
                    print("An exception occured: ", str(e))
                

                frames_chunk = []
                frames_counter = 0
                # return


                # wait for the operator response: ...

                # delete all the chunk of frame from DoneImages folder:
                auxiliary_functions.delete_files_in_directory(folder_name="PendingImages")
            
            frame_index+=1


        # Release the video capture
        vid.release()
        time2 = time.time()
        print(f"::: Total running time: {time2 - time1}")

    def send_frames_to_operator(self, frames_chunk, model_output_list):
        
        # frames_chunk = [(frame, id), (), ()]
        # frame_id = frame_and_id[1]

        model_output_list = [x.split(".")[0] for x in model_output_list]
        frames_chunk_to_send = [frame_and_id for frame_and_id in frames_chunk if frame_and_id[1] in model_output_list]

        # for x in frames_chunk:
        #     print(f':::frame_id = {x[1]} :::::')

        print(f"len(frames_chunk_to_send) = {len(frames_chunk_to_send)}")

        # for frame, frame_id in frames_chunk:
        for frame, frame_id in frames_chunk_to_send:
            # Encode the frame:
            WIDTH = 400
            frame = imutils.resize(frame, width=WIDTH)
            print(f"frame_id = {frame_id}")
            encoded_succes, encoded_frame = cv2.imencode(
            '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

            # Serialize the frame into a byte array
            id_and_frame = (frame_id, encoded_frame)
            message = pickle.dumps(id_and_frame)

            message = bytes(f'{len(message): < {HEADERSIZE}}', "utf-8") + message
            self.model_server_socket.sendto(message, self.client_addr)

        id_and_frame = ('FINISH', None)
        message = pickle.dumps(id_and_frame)
        message = bytes(f'{len(message): < {HEADERSIZE}}', "utf-8") + message
        self.model_server_socket.sendto(message, self.client_addr)

        print("Close the socket connection")
        self.model_server_socket.close()


        
    def save_frame_on_disk(self, frame, dest):
        buffer_id = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
        full_path = os.path.join(dest, buffer_id) + ".jpg"
        # print(f"full_path = {full_path}")

        cv2.imwrite(full_path + ".jpg", frame)

        return (frame, buffer_id)


    def save_video_frames(self, video_name):
            print(":: save_video_frames :: ")
            # Get the full path of the current file
            _, static_folder_location = self.get_src_vid_path()
            pending_images_folder = 'C:\\Users\\project25\\RescueSign\\PendingImages'

            video_src = static_folder_location + "\\" + self.video_name
            print(f"video_src = {video_src}")

            # # Open the video file or capture from a camera
            vid = cv2.VideoCapture(video_src)

            total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"total frames = {total_frames}")

            current_frame = 0

            frame_rate = 6  # Desired frame rate (6 frames per second)
            frame_interval = 1 / frame_rate  # Interval between frames
            start_time = time.time()  # Update start time

            while vid.isOpened():
                return_val, frame = vid.read()
                if not return_val:
                    break

                # Calculate the elapsed time since the last frame
                elapsed_time = time.time() - start_time

                # If the elapsed time is greater than the frame interval, send the frame
                if elapsed_time >= frame_interval:
                    buffer_id = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
                    full_path = os.path.join(pending_images_folder, buffer_id) + ".jpg"


                    # Save the frame as image:
                    cv2.imwrite(full_path + ".jpg", frame)
                    


                    #############################################
                    start_time = time.time()  # Update the start time

                current_frame +=1
            # Release the video capture
            vid.release()



    def send_video_frames(self):
    
        # Get the full path of the current file
        path_out, dir_name = self.get_src_vid_path()
        video_src = f'{dir_name}/{self.video_name}'

        # Open the video file or capture from a camera
        vid = cv2.VideoCapture(video_src)

        frame_rate = 6  # Desired frame rate (6 frames per second)
        frame_interval = 1 / frame_rate  # Interval between frames
        start_time = time.time()  # Update start time

        while vid.isOpened():
            # start_time = time.time()  # Initialize start time
            return_val, frame = vid.read()
            if not return_val:
                id_and_frame = ('FINISH', None)
                message = pickle.dumps(id_and_frame)
                message = bytes(f'{len(message): < {HEADERSIZE}}', "utf-8") + message
                self.model_server_socket.sendto(message, self.client_addr)

                print("Close the socket connection")
                self.model_server_socket.close()
                break

            # Calculate the elapsed time since the last frame
            elapsed_time = time.time() - start_time

            # If the elapsed time is greater than the frame interval, send the frame
            if elapsed_time >= frame_interval:
                # ... (send the frame)
                WIDTH = 400
                frame = imutils.resize(frame, width=WIDTH)

                buffer_id = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
                full_path = os.path.join(path_out, buffer_id)

                print(f"buffer_id = {buffer_id}")

                # Save the frame as image:
                cv2.imwrite(path_out + ".jpg", frame)

                # Encode the frame:
                encoded_succes, encoded_frame = cv2.imencode(
                    '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

                # Serialize the frame into a byte array
                id_and_frame = (buffer_id, encoded_frame)
                message = pickle.dumps(id_and_frame)
                # frame_data = pickle.dumps(encoded_frame)

                # message = pickle.dumps(frame_data)
                message = bytes(
                    f'{len(message): < {HEADERSIZE}}', "utf-8") + message
                self.model_server_socket.sendto(message, self.client_addr)

                #############################################
                start_time = time.time()  # Update the start time



        # Release the video capture
        vid.release()



