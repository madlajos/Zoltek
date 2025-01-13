import { Component, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { SharedService } from '../../shared.service';

@Component({
  selector: 'app-image-viewer',
  templateUrl: './image-viewer.component.html',
  styleUrls: ['./image-viewer.component.css']
})
export class ImageViewerComponent implements AfterViewInit {
  @ViewChild('mainVideoContainer', { static: false }) mainVideoContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('sideVideoContainer', { static: false }) sideVideoContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('imageOverlay', { static: false }) imageOverlay!: ElementRef<HTMLDivElement>;

  isMainStreaming: boolean = false;
  isSideStreaming: boolean = false;

  isMainConnected: boolean = false;
  isSideConnected: boolean = false;

  mainButton1Icon: string = 'play_arrow';
  mainButton2Icon: string = 'link';
  sideButton1Icon: string = 'play_arrow';
  sideButton2Icon: string = 'link';

  mainCameraName: string = 'No main camera connected';
  sideCameraName: string = 'No side camera connected';

  private readonly BASE_URL = 'http://localhost:5000/api';

  images: string[] = [];
  selectedImage: string | null = null;

  constructor(private http: HttpClient, private sharedService: SharedService) { }

  ngAfterViewInit(): void {
    this.displayPlaceholder('main');
    this.displayPlaceholder('side');
    this.checkCameraConnection('main');
    this.checkCameraConnection('side');
  
    // ✅ Subscribe to camera connection status to update buttons reactively
    this.sharedService.cameraConnectionStatus$.subscribe((status) => {
      this.isMainConnected = status.main;
      this.isSideConnected = status.side;
  
      // ✅ Update button icons dynamically
      this.mainButton2Icon = this.isMainConnected ? 'link_off' : 'link';
      this.sideButton2Icon = this.isSideConnected ? 'link_off' : 'link';
  
      // ✅ Enable/disable stream buttons when connection status changes
      this.updateButtonStyles('main');
      this.updateButtonStyles('side');
    });

    this.sharedService.cameraStreamStatus$.subscribe(status => {
      this.isMainStreaming = status.main;
      this.isSideStreaming = status.side;
  
      this.mainButton1Icon = this.isMainStreaming ? 'stop' : 'play_arrow';
      this.sideButton1Icon = this.isSideStreaming ? 'stop' : 'play_arrow';

      this.updateButtonStyles('main');
      this.updateButtonStyles('side');
  
      console.log(`Stream Status - Main: ${this.isMainStreaming}, Side: ${this.isSideStreaming}`);
    });
  
    this.sharedService.selectedImage$.subscribe(imagePath => {
      if (imagePath) {
        this.showImage(imagePath);
      }
    });
  
    // ✅ Initial connection check
    this.checkCameraConnection('main');
    this.checkCameraConnection('side');
  }
  

  checkCameraConnection(cameraType: 'main' | 'side'): void {
    this.http.get(`http://localhost:5000/api/status/camera?type=${cameraType}`).subscribe(
      (response: any) => {
        const wasConnected = cameraType === 'main' ? this.isMainConnected : this.isSideConnected;
  
        if (response.connected !== wasConnected) {
          // Only update if the status actually changes
          if (cameraType === 'main') {
            this.isMainConnected = response.connected;
            this.mainButton2Icon = response.connected ? 'link_off' : 'link';
          } else {
            this.isSideConnected = response.connected;
            this.sideButton2Icon = response.connected ? 'link_off' : 'link';
          }
  
          this.sharedService.setCameraConnectionStatus(cameraType, response.connected);
          this.updateButtonStyles(cameraType);
  
          console.log(`${cameraType.toUpperCase()} Camera connection status updated: ${response.connected}`);
        }
      },
      error => {
        console.error(`Failed to check ${cameraType} camera status:`, error);
      }
    );
  }
  


  getCameraName(cameraType: 'main' | 'side'): void {
    this.http.get(`http://localhost:5000/api/camera-name?type=${cameraType}`).subscribe(
      (response: any) => {
        if (cameraType === 'main') {
          this.mainCameraName = response.name;
        } else {
          this.sideCameraName = response.name;
        }
      },
      error => {
        console.error(`Failed to get ${cameraType} camera name:`, error);
      }
    );
  }

  toggleStream(cameraType: 'main' | 'side'): void {
    const isConnected = cameraType === 'main' ? this.isMainConnected : this.isSideConnected;
  
    if (!isConnected) {
      console.warn(`Cannot start stream. ${cameraType.toUpperCase()} camera is not connected.`);
      return;
    }
  
    if (cameraType === 'main') {
      if (this.isMainStreaming) {
        console.log('Stopping MAIN camera stream...');
        this.stopVideoStream('main');
      } else {
        console.log('Starting MAIN camera stream...');
        this.startVideoStream('main');
      }
    } else {
      if (this.isSideStreaming) {
        console.log('Stopping SIDE camera stream...');
        this.stopVideoStream('side');
      } else {
        console.log('Starting SIDE camera stream...');
        this.startVideoStream('side');
      }
    }
  }
  
  startVideoStream(cameraType: 'main' | 'side'): void {
    console.log(`Starting stream for ${cameraType} camera`);
  
    const videoContainer = cameraType === 'main' ? this.mainVideoContainer.nativeElement : this.sideVideoContainer.nativeElement;
    const streamUrl = `http://localhost:5000/start-video-stream?type=${cameraType}&${new Date().getTime()}`;
  
    const img = document.createElement('img');
    img.src = streamUrl;
    img.style.width = '100%';
    img.style.height = '100%';
  
    videoContainer.innerHTML = '';
    videoContainer.appendChild(img);
  
    if (cameraType === 'main') {
      this.isMainStreaming = true;
      this.mainButton1Icon = 'stop';
    } else {
      this.isSideStreaming = true;
      this.sideButton1Icon = 'stop';
    }
  }
  

  stopVideoStream(cameraType: 'main' | 'side'): void {
    if ((cameraType === 'main' && !this.isMainStreaming) || (cameraType === 'side' && !this.isSideStreaming)) {
      return;  // Exit if already stopped
    }
  
    this.http.post(`http://localhost:5000/stop-video-stream?type=${cameraType}`, {}).subscribe(
      response => {
        const videoContainer = cameraType === 'main' ? this.mainVideoContainer.nativeElement : this.sideVideoContainer.nativeElement;
        videoContainer.innerHTML = '';  // Clear the video container
        this.displayPlaceholder(cameraType);  // Display placeholder
  
        if (cameraType === 'main') {
          this.isMainStreaming = false;
          this.mainButton1Icon = 'play_arrow';
        } else {
          this.isSideStreaming = false;
          this.sideButton1Icon = 'play_arrow';
        }
  
        console.log(`${cameraType.toUpperCase()} camera stream stopped`);
      },
      error => {
        console.error(`Failed to stop ${cameraType} video stream:`, error);
      }
    );
  }

  toggleConnection(cameraType: 'main' | 'side'): void {
    if (cameraType === 'main' && this.isMainConnected) {
      this.disconnectCamera('main');
    } else if (cameraType === 'side' && this.isSideConnected) {
      this.disconnectCamera('side');
    } else {
      this.connectCamera(cameraType);
    }
  }

  connectCamera(cameraType: 'main' | 'side'): void {
    console.log(`Attempting to connect ${cameraType} camera...`);
  
    this.http.post(`http://localhost:5000/connect-camera?type=${cameraType}`, {}).subscribe(
      (response: any) => {
        const isConnected = response.connected;
        const cameraDetails = `${response.name} (${response.serial || 'No Serial'})`;
  
        if (isConnected) {
          if (cameraType === 'main') {
            this.isMainConnected = true;
            this.mainButton2Icon = 'link_off';
            this.mainCameraName = cameraDetails;
          } else {
            this.isSideConnected = true;
            this.sideButton2Icon = 'link_off';
            this.sideCameraName = cameraDetails;
          }
  
          this.sharedService.setCameraConnectionStatus(cameraType, true);
          this.updateButtonStyles(cameraType);
  
          console.log(`${cameraType.toUpperCase()} Camera connected: ${cameraDetails}`);
        } else {
          console.warn(`${cameraType.toUpperCase()} camera connection failed.`);
        }
      },
      error => {
        console.error(`Failed to connect ${cameraType} camera:`, error);
      }
    );
  }
  
  
  
  


  disconnectCamera(cameraType: 'main' | 'side'): void {
    if ((cameraType === 'main' && this.isMainStreaming) || (cameraType === 'side' && this.isSideStreaming)) {
      this.stopVideoStream(cameraType);
    }

    this.http.post(`http://localhost:5000/disconnect-camera?type=${cameraType}`, {}).subscribe(
      response => {
        if (cameraType === 'main') {
          this.isMainConnected = false;
          this.mainButton2Icon = 'link';
          this.mainCameraName = 'No main camera connected';
        } else {
          this.isSideConnected = false;
          this.sideButton2Icon = 'link';
          this.sideCameraName = 'No side camera connected';
        }
        this.updateButtonStyles(cameraType);
        console.log(`${cameraType.toUpperCase()} Camera disconnected`);
      },
      error => {
        console.error(`Failed to disconnect ${cameraType} camera:`, error);
      }
    );
  }

  saveImage(cameraType: 'main' | 'side'): void {
    const isConnected = cameraType === 'main' ? this.isMainConnected : this.isSideConnected;

    if (!isConnected) {
      console.warn(`Cannot save image. ${cameraType.toUpperCase()} camera is not connected.`);
      return;
    }

    const saveDirectory = this.sharedService.getSaveDirectory();
    if (!saveDirectory) {
      console.error('Save directory is empty.');
      return;
    }

    this.http.post(`http://localhost:5000/api/save-image?type=${cameraType}`, { save_directory: saveDirectory }).subscribe(
      (response: any) => {
        this.images.push(response.filename);
        console.log(`Image from ${cameraType} camera saved as ${response.filename}`);
      },
      error => {
        console.error(`Failed to save image from ${cameraType} camera:`, error);
      }
    );
  }

  updateButtonStyles(cameraType: 'main' | 'side'): void {
    // ✅ Select UI elements based on camera type
    const connectButton = document.querySelector(`.${cameraType}-connect-button`) as HTMLElement;
    const streamButton = document.querySelector(`.${cameraType}-stream-button`) as HTMLElement;
    const saveButton = document.querySelector(`.${cameraType}-save-button`) as HTMLElement;
  
    const isConnected = cameraType === 'main' ? this.isMainConnected : this.isSideConnected;
  
    if (connectButton && streamButton && saveButton) {
      if (isConnected) {
        // 🔵 Enable buttons and change styling
        connectButton.style.backgroundColor = '#2a628c';
        streamButton.style.backgroundColor = '#2a628c';
        saveButton.style.backgroundColor = '#2a628c';
  
        streamButton.removeAttribute('disabled');
        saveButton.removeAttribute('disabled');
        connectButton.innerHTML = '<mat-icon>link_off</mat-icon>';  // 🔗 Show disconnect icon
      } else {
        // 🔴 Disable buttons and reset styling
        connectButton.style.backgroundColor = '#555';
        streamButton.style.backgroundColor = '#555';
        saveButton.style.backgroundColor = '#555';
  
        streamButton.setAttribute('disabled', 'true');
        saveButton.setAttribute('disabled', 'true');
        connectButton.innerHTML = '<mat-icon>link</mat-icon>';  // 🔗 Show connect icon
      }
    } else {
      console.warn(`❗ UI buttons for ${cameraType} camera not found.`);
    }
  }
  

  displayPlaceholder(cameraType: 'main' | 'side'): void {
    const videoContainer = cameraType === 'main' ? this.mainVideoContainer.nativeElement : this.sideVideoContainer.nativeElement;

    const placeholder = document.createElement('div');
    placeholder.className = 'placeholder';
    placeholder.innerText = `[LIVE VIEW - ${cameraType.toUpperCase()} CAMERA]`;

    videoContainer.innerHTML = '';
    videoContainer.appendChild(placeholder);
  }

  showImage(imagePath: string): void {
    this.selectedImage = imagePath;
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
