from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import os
# from RESCUEDIGN. import ModelSocket
from model_socket_class import ModelSocket
import sys
import time
from Rescue_Sign import RescueSignModel
import auxiliary_functions

app = Flask(__name__)
CORS(app)

module_directory = r'C:\Users\project25\RescueSign\Rescue_Sign.py'
sys.path.append(module_directory)



@app.route('/response_from_operator', methods=['POST'])
def get_response():
    data = request.json

    print(f'operator response: {data}')

    return 'POST request received'

@app.route('/model_ui', methods=['GET'])
def model_ui():
    # open_operator_socket()
    return render_template('model_ui.html')

@app.route('/get_file_names')
def get_file_names():
    
    # Get the full path of the current file
    file_path = os.path.abspath(__file__) # Rescue_Sign_SERVER_proj\model_server_UI.py
    # Get the directory name of the current file
    dir_path = os.path.dirname(file_path) + '/static'

    file_names = [file for file in os.listdir(dir_path) if (file.endswith('.mp4')) or (file.endswith('.MOV'))]

    return jsonify(file_names)

@app.route('/process_file', methods=['POST'])
def process_file():
    print(":: process_file ::")
    data = request.get_json()
    video_name = data['option']


   # model_socket.send_frames_by_chunks()
    auxiliary_functions.clean_model_folders()

    # Save the frames and then sends them to the model 
    model_socket = ModelSocket(video_name)

    # model_socket.save_video_frames(video_name)
    model_socket.send_frames_by_chunks()


    auxiliary_functions.clean_model_folders()


    # Call the model on the video frames:
    # model = RescueSignModel()
    # model.run_model()

    # print(f":::: model.output :::")
    # print(model.output)   

    # model_socket.create_socket_and_bind_it()

    # start_time = time.time()
    # model_socket.send_video_frames()
    # end_time = time.time()
    # execution_time = end_time - start_time
    # print(f":::: execution_time = {execution_time}")

    return 'Option received'

# @app.route('/')
# def index():
#     return render_template('main_model_UI.html')


# def open_operator_socket():
#     print("::: open_operator_socket() ::::")
#     import requests
#     url = "http://127.0.0.1:5050/create_socket_connection"

#     headers = {
#         'Content-Type': 'application/json'
#     }

#     # Send a GET request:
#     response = requests.get(url, headers=headers)

#     # Check the response status code
#     if response.status_code == 200:  # 200 indicates a successful request
#         # Access the response content
#         data = response.json()  # Assuming the response is in JSON format
#         # Process the data or perform further operations
#         print(data)
#     else:
#         print("GET request failed with status code:", response.status_code)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=44444)