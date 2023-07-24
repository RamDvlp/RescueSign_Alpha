
console.log("::::::::::::::::::::::: ")

// Show the video element and the "Watch Video" button
var videoDisplay = document.getElementById('video-display');
var watchVideoButton = document.getElementById('watch-video-btn');
videoDisplay.style.display = 'none';
watchVideoButton.style.display = 'block';


function watchVideo() {
    var select = document.getElementById('file-select');
    var selectedOption = select.options[select.selectedIndex].text;
    console.log("::: selectedOption = ", selectedOption)

    var videoUrl = '/static/' + selectedOption;

    var videoPlayer = document.createElement('video');

    videoPlayer.src = videoUrl;

    videoPlayer.controls = true;

    var videoContainer = document.getElementById('video-container');
    videoContainer.innerHTML = '';
    videoContainer.appendChild(videoPlayer);

    videoPlayer.width = 600; // Set the width to 600 pixels
}


function uploadFile() {
    var select = document.getElementById('file-select');
    console.log("::: uploadFile() :: ");
    var selectedOption = select.options[select.selectedIndex].text;
    

    fetch('/process_file', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ option: selectedOption})
    })
    .then(response => {
        console.log("Server response: ", response);
    })
}

function populateFileSelect(fileNames) {
    var select = document.getElementById('file-select');
    select.innerHTML = ''; // Clear existing options

    fileNames.forEach(fileName => {
        var option = document.createElement('option');
        option.text = fileName;
        select.add(option);
    });
}

function fetchFileNamesFromServer() {
    fetch('/get_file_names')
        .then(response => response.json())
        .then(data => {
            console.log("data = ", data);
            populateFileSelect(data);
        })
        .catch(error => {
            console.error('Error: ', error);
        });
}

fetchFileNamesFromServer();