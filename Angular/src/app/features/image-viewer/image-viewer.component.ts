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
  @ViewChild('imageOverlay', { static: false }) imageOverlay!: ElementRef<HTMLDivElement>;
  isStreaming: boolean = false;
  isConnected: boolean = false;
  button1Icon: string = 'play_arrow';
  button2Icon: string = 'link';
  cameraName: string = 'No camera connected';
  images: string[] = [];
  selectedImage: string | null = null;

  constructor(private http: HttpClient, private sharedService: SharedService) { }

  ngAfterViewInit(): void {
    this.displayPlaceholder();
    this.checkCameraConnection();
    this.sharedService.selectedImage$.subscribe(imagePath => {
      if (imagePath) {
        this.showImage(imagePath);
      }
    });
  }

  checkCameraConnection(): void {
    this.http.get('http://localhost:5000/api/status/camera').subscribe(
      (response: any) => {
        this.isConnected = response.connected;
        this.updateButtonStyles();
        this.sharedService.setCameraConnectionStatus(this.isConnected);
        if (this.isConnected) {
          this.button2Icon = 'link_off';
          this.getCameraName();
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
    if (this.isStreaming) {
      return; // Exit if the stream is already running
    }

    this.isStreaming = true;
    this.button1Icon = 'stop';

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
    if (!this.isStreaming) {
      return; // Exit if the stream is already stopped
    }

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
        this.sharedService.setCameraConnectionStatus(this.isConnected);
        console.log('Camera connected');
        this.getCameraName();
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
        this.sharedService.setCameraConnectionStatus(this.isConnected);
        console.log('Camera disconnected');
        this.cameraName = 'No camera connected';
      },
      error => {
        console.error('Failed to disconnect camera:', error);
      }
    );
  }

  saveImage(): void {
    if (!this.isConnected) {
      console.warn('Cannot save image. Camera is not connected.');
      return;
    }

    const saveDirectory = this.sharedService.getSaveDirectory();
    if (!saveDirectory) {
      console.error('Save directory is empty.');
      return;
    }

    this.http.post('http://localhost:5000/api/save-image', { save_directory: saveDirectory }).subscribe(
      (response: any) => {
        this.images.push(response.filename);
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
      connectButton.style.backgroundColor = '#2a628c';
      streamButton.removeAttribute('disabled');
      saveButton.style.backgroundColor = '#2a628c';
      saveButton.removeAttribute('disabled');
    } else {
      connectButton.style.backgroundColor = '#555';
      streamButton.setAttribute('disabled', 'true');
      saveButton.style.backgroundColor = '#555';
      saveButton.setAttribute('disabled', 'true');
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

  showImage(imagePath: string): void {
    this.selectedImage = imagePath;  // Set the current image
    const imageOverlay = this.imageOverlay.nativeElement;

    const img = document.createElement('img');
    img.src = `http://localhost:5000/images/${imagePath}`;
    img.style.width = '100%';
    img.style.height = '100%';

    imageOverlay.innerHTML = '';
    imageOverlay.appendChild(img);
    imageOverlay.style.display = 'flex';
  }

  clearImage(): void {
    this.selectedImage = null;
    const imageOverlay = this.imageOverlay.nativeElement;
    imageOverlay.style.display = 'none';
  }
}
