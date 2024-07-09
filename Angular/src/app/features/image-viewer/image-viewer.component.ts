import { Component, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-image-viewer',
  templateUrl: './image-viewer.component.html',
  styleUrls: ['./image-viewer.component.css']
})
export class ImageViewerComponent implements AfterViewInit {
  @ViewChild('videoContainer', { static: false }) videoContainer!: ElementRef<HTMLDivElement>;
  isStreaming: boolean = false; // Track if the stream is active
  isConnected: boolean = false; // Track if the camera is connected
  button1Icon: string = 'play_arrow'; // Initial icon for Button 1
  button2Icon: string = 'link'; // Initial icon for Button 2
  saveDirectory: string = ''; // Store the selected save directory
  cameraName: string = 'No camera connected'; // Initial camera name

  constructor(private http: HttpClient) { }

  ngAfterViewInit(): void {
    this.displayPlaceholder();
    this.checkCameraConnection();
  }

  checkCameraConnection(): void {
    this.http.get('http://localhost:5000/api/status/camera').subscribe(
      (response: any) => {
        this.isConnected = response.connected;
        this.updateButtonStyles();
        if (this.isConnected) {
          this.button2Icon = 'link_off';
          this.getCameraName();
        } else {
          this.button2Icon = 'link';
          this.cameraName = 'No camera connected';
        }
      },
      error => {
        console.error('Failed to check camera status:', error);
      }
    );
  }

  getCameraName(): void {
    this.http.get('http://localhost:5000/api/camera-name').subscribe(
      (response: any) => {
        this.cameraName = response.name;
      },
      error => {
        console.error('Failed to get camera name:', error);
      }
    );
  }

  toggleStream(): void {
    if (!this.isConnected) {
      console.warn('Cannot start stream. Camera is not connected.');
      return;
    }

    if (this.isStreaming) {
      this.stopVideoStream();
    } else {
      this.startVideoStream();
    }
  }

  startVideoStream(): void {
    this.isStreaming = true;
    this.button1Icon = 'stop';

    // Add a timestamp to the video URL to prevent caching
    const videoUrl = `http://localhost:5000/video-stream?${new Date().getTime()}`;
    const videoContainer = this.videoContainer.nativeElement;

    const img = document.createElement('img');
    img.src = videoUrl;
    img.style.width = '100%';
    img.style.height = '100%';

    videoContainer.innerHTML = '';
    videoContainer.appendChild(img);
  }

  stopVideoStream(): void {
    this.isStreaming = false;
    this.button1Icon = 'play_arrow';

    this.http.post('http://localhost:5000/stop-video-stream', {}).subscribe(
      response => {
        const videoContainer = this.videoContainer.nativeElement;
        videoContainer.innerHTML = ''; // Clear the video container
        this.displayPlaceholder(); // Display placeholder
      },
      error => {
        console.error('Failed to stop video stream:', error);
      }
    );
  }

  toggleConnection(): void {
    if (this.isConnected) {
      this.disconnectCamera();
      this.cameraName = 'No camera connected';
    } else {
      this.connectCamera();
    }
  }

  connectCamera(): void {
    this.http.post('http://localhost:5000/connect-camera', {}).subscribe(
      response => {
        this.isConnected = true;
        this.button2Icon = 'link_off';
        this.updateButtonStyles();
        console.log('Camera connected');
      },
      error => {
        console.error('Failed to connect camera:', error);
      }
    );
  }

  disconnectCamera(): void {
    if (this.isStreaming) {
      this.stopVideoStream();
    }
    this.http.post('http://localhost:5000/disconnect-camera', {}).subscribe(
      response => {
        this.isConnected = false;
        this.button2Icon = 'link';
        this.updateButtonStyles();
        console.log('Camera disconnected');
      },
      error => {
        console.error('Failed to disconnect camera:', error);
      }
    );
  }

  updateButtonStyles(): void {
    const connectButton = document.querySelector('.connect-button') as HTMLElement;
    const streamButton = document.querySelector('.stream-button') as HTMLElement;
    const saveButton = document.querySelector('.save-button') as HTMLElement;

    if (this.isConnected) {
      connectButton.style.backgroundColor = '#2a628c'; // Connected color
      streamButton.removeAttribute('disabled'); // Enable stream button
      saveButton.removeAttribute('disabled'); // Enable save button
    } else {
      connectButton.style.backgroundColor = '#555'; // Default color
      streamButton.setAttribute('disabled', 'true'); // Disable stream button
      saveButton.setAttribute('disabled', 'true'); // Disable save button
    }
  }

  displayPlaceholder(): void {
    const videoContainer = this.videoContainer.nativeElement;

    const placeholder = document.createElement('div');
    placeholder.className = 'placeholder';
    placeholder.innerText = '[LIVE VIEW]';

    videoContainer.innerHTML = '';
    videoContainer.appendChild(placeholder);
  }

  saveImage(): void {
    if (!this.isConnected) {
      console.warn('Cannot save image. Camera is not connected.');
      return;
    }
  
    // Logic to capture and save image
    const saveDirectory = this.saveDirectory; // Use the save directory from your other component or service
    const imageData = 'base64EncodedImageData'; // This should be the actual image data
  
    this.http.post('http://localhost:5000/api/save-image', { save_directory: saveDirectory, image_data: imageData }).subscribe(
      (response: any) => {
        console.log('Image saved:', response.path);
      },
      error => {
        console.error('Failed to save image:', error);
      }
    );
  }
}
