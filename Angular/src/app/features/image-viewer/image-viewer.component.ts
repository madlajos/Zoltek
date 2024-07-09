import { Component, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { SharedService } from '../../shared.service';

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
  cameraName: string = 'No camera connected'; // Initial camera name

  constructor(private http: HttpClient, private sharedService: SharedService) { }

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
          this.getCameraName(); // Fetch the camera name if connected
        } else {
          this.button2Icon = 'link';
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
        this.getCameraName(); // Fetch the camera name after connecting
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
        this.cameraName = 'No camera connected';
      },
      error => {
        console.error('Failed to disconnect camera:', error);
      }
    );
  }

  saveImage(): void {
    console.log('Save image button clicked.');
    if (!this.isConnected) {
      console.warn('Cannot save image. Camera is not connected.');
      return;
    }
  
    const saveDirectory = this.sharedService.getSaveDirectory(); // Get save directory from SharedService
    console.log(`Save directory: ${saveDirectory}`);
    if (!saveDirectory) {
      console.error('Save directory is empty.');
      return;
    }
  
    this.http.post('http://localhost:5000/api/save-image', { save_directory: saveDirectory }).subscribe(
      (response: any) => {
        console.log('Image saved:', response.path);
        // Reload images after saving if needed
      },
      error => {
        console.error('Failed to save image:', error);
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
      saveButton.style.backgroundColor = '#2a628c'; // Enable save button
      saveButton.removeAttribute('disabled'); // Enable save button
    } else {
      connectButton.style.backgroundColor = '#555'; // Default color
      streamButton.setAttribute('disabled', 'true'); // Disable stream button
      saveButton.style.backgroundColor = '#555'; // Disable save button
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
}
