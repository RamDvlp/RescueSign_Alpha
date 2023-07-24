import os
from os import listdir
import shutil
from ultralytics import YOLO
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

class RescueSignModel:
    def __init__(self):
        # Print the current working directory
        print("Current working directory: {0}".format(os.getcwd()))
        if os.getcwd().split('\\')[-1] != "openpose":
            # Change the current working directory
            os.chdir('..\Anaconda3\openpose')
            # Print the current working directory
            print("Current working directory: {0}".format(os.getcwd()))

        self.proj_dir = r"C:\Users\project25\RescueSign"
        self.input_images_dir = r"C:\Users\project25\RescueSign\PendingImages"
        self.in_progress_images_dir = r"C:\Users\project25\RescueSign\InProgressImages"
        self.done_input_images_dir = r"C:\Users\project25\RescueSign\DoneImages"

        self.cropped_images_dir = r"C:\Users\project25\RescueSign\CroppedImages\crops\person"
        self.cropped_images_parent_dir = r"C:\Users\project25\RescueSign\CroppedImages\crops"
        self.cropped_images_parent2_dir = r"C:\Users\project25\RescueSign\CroppedImages"
        self.done_cropped_images_dir = r"C:\Users\project25\RescueSign\DoneCroppedImages"

        self.openpose_jsons_path = r"C:\Users\project25\RescueSign\OpenPoseJsons"
        self.done_openpose_jsons_path = r"C:\Users\project25\RescueSign\DoneOpenPoseJsons"

        self.rescue_sign_model_path = r"C:\Users\project25\RescueSign\RescueSignModel2.pth"

        self.yolov8_model = YOLO("yolov8m.pt")

        self.__device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        torch.cuda.empty_cache()
        self.__rescue_sign_model = RescueSignNet()
        self.__rescue_sign_model.load_state_dict(torch.load(self.rescue_sign_model_path))
        self.__rescue_sign_model.to(device=self.__device)


    def run_model(self):
        self.__move_files_to_new_dir(self.input_images_dir, self.in_progress_images_dir)

        self.__crop_people_using_yolo()

        self.__pose_estimation_using_openpose()

        self.__prepare_pose_classification_model()
        self.__predict()
        self.__prepare_output_list()


    def __move_files_to_new_dir(self, old_dir, new_dir):
        file_names = listdir(old_dir)
        for file_name in file_names:
            shutil.move(os.path.join(old_dir, file_name), os.path.join(new_dir, file_name))


    def __crop_people_using_yolo(self):    
        self.yolov8_model.predict(self.in_progress_images_dir, project=self.proj_dir, name=r"CroppedImages", imgsz=640, conf=0.7, device=0, save=False, save_crop=True, hide_labels=True, hide_conf=True, classes=0)

        self.__move_files_to_new_dir(self.in_progress_images_dir, self.done_input_images_dir)


    def __read_jsons_from_directory(self, path_to_json_files):
        #get all JSON file names as a list
        json_file_names = os.listdir(path_to_json_files)

        frames_res = []

        for json_file_name in json_file_names:
            with open(os.path.join(path_to_json_files, json_file_name)) as json_file:
                jsonContent = json_file.read()
                frames_res.append(json.loads(jsonContent))

        key_points = []
        for frame, json_file_name in zip(frames_res, json_file_names):
            for person in frame['people']:
                key_points.append((json_file_name, []))
                person_keypoints = person['pose_keypoints_2d']
                for i, keypoint in enumerate(person_keypoints, 1):
                    if i%3 != 0:
                        key_points[-1][1].append(keypoint)

        return key_points
    

    def __pose_estimation_using_openpose(self):
        if os.path.isdir(self.cropped_images_dir):
            os.system(f'bin\\OpenPoseDemo.exe --image_dir {self.cropped_images_dir} --write_json {self.openpose_jsons_path} --display 0 --render_pose 0 --disable_blending')

            self.__key_points = self.__read_jsons_from_directory(self.openpose_jsons_path)

            self.__move_files_to_new_dir(self.cropped_images_dir, self.done_cropped_images_dir)
            self.__move_files_to_new_dir(self.openpose_jsons_path, self.done_openpose_jsons_path)

            # Delete yolov8 result directory to avoid creating new directories (eg. 'C:\Users\project25\RescueSign\CroppedImages2')
            paths = [self.cropped_images_dir, self.cropped_images_parent_dir, self.cropped_images_parent2_dir]
            for path in paths:
                try:
                    os.rmdir(path)
                    print("directory is deleted")
                except OSError as x:
                    print("Error occured: %s : %s" % (path, x.strerror))
        else:
            self.__key_points = []

    def __prepare_pose_classification_model(self):
        keypoints_dataset = RescueSignDataset(self.__key_points)
        self.__keypoints_loader = DataLoader(keypoints_dataset, batch_size=32, shuffle=False)        

        self.__rescue_sign_model.eval()

    def __predict(self):
        self.__predicted = [] 
        threshold = torch.tensor([0.5])
        threshold = threshold.to(self.__device)

        with torch.no_grad():
            for names, inputs in self.__keypoints_loader:
                inputs = inputs.to(self.__device)
                outputs = self.__rescue_sign_model(inputs)

                outputs_thresh = (outputs>threshold).float()
                self.__predicted += zip(names, outputs_thresh.tolist())

                # self.__predicted += zip(names, torch.round(outputs).tolist())

    def __prepare_output_list(self):
        self.output = []
        for json_name, pred in self.__predicted:
            if pred == 1:
                self.output.append(json_name.split("_keypoints")[0] + ".jpg")

        self.output = list(set(self.output))


class RescueSignDataset(Dataset):
    def __init__(self, keypoints, labels=None):
        self.jsons_names = []
        self.keypoints = []
        for person in keypoints:
            self.jsons_names.append(person[0])
            self.keypoints.append(torch.tensor(person[1], dtype=torch.float32))
        if labels is not None:
            self.labels = torch.tensor(labels, dtype=torch.float32)
        else:
            self.labels = None
    def __len__(self):
        return len(self.keypoints)
    def __getitem__(self, index):
        if self.labels is not None:
            return self.keypoints[index], self.labels[index]
        return self.jsons_names[index], self.keypoints[index]
        

class RescueSignNet(nn.Module):
    def __init__(self):
        super(RescueSignNet, self).__init__()
        self.layer1 = nn.Sequential(
            nn.Linear(50, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
        )
        self.layer2 = nn.Sequential(
            nn.Linear(128, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.5)
        )
        self.layer3 = nn.Sequential(
            nn.Linear(256, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.6)
        )
        self.layer4 = nn.Sequential(
            nn.Linear(256, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.7)
        )
        self.layer5 = nn.Sequential(
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.6)
        )
        self.layer6 = nn.Sequential(
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.5)
        )
        self.layer7 = nn.Sequential(
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
  
    def forward(self, x):
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.layer5(x)
        x = self.layer6(x)
        x = self.layer7(x)
        return x.view(-1)