import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs/operators';


@Injectable({
  providedIn: 'root'
})
export class SharedService {
  private cameraConnectionStatus = new BehaviorSubject<{ main: boolean; side: boolean }>({
    main: false,
    side: false
  });
  cameraConnectionStatus$ = this.cameraConnectionStatus.asObservable();

  private cameraStreamStatus = new BehaviorSubject<{ main: boolean; side: boolean }>({
    main: false,
    side: false
  });
  cameraStreamStatus$ = this.cameraStreamStatus.asObservable();

  isMainConnected$ = this.cameraConnectionStatus.asObservable().pipe(map(status => status.main));
  isSideConnected$ = this.cameraConnectionStatus.asObservable().pipe(map(status => status.side));

  isMainStreaming$ = this.cameraStreamStatus.asObservable().pipe(map(status => status.main));
  isSideStreaming$ = this.cameraStreamStatus.asObservable().pipe(map(status => status.side));

  private saveDirectory: string = '';

  constructor(private http: HttpClient) {}

  setSaveDirectory(directory: string): void {
    this.saveDirectory = directory;
    console.log(`Save directory set to: ${directory}`);
  }

  getSaveDirectory(): string {
    console.log(`Retrieving save directory: ${this.saveDirectory}`);
    return this.saveDirectory;
  }

  setCameraConnectionStatus(cameraType: 'main' | 'side', status: boolean): void {
    const currentStatus = this.cameraConnectionStatus.getValue();
    const updatedStatus = { ...currentStatus, [cameraType]: status };
    this.cameraConnectionStatus.next(updatedStatus);

    console.log(`Updated ${cameraType} camera connection status to: ${status}`);
  }

  setCameraStreamStatus(cameraType: 'main' | 'side', isStreaming: boolean): void {
    const currentStatus = this.cameraStreamStatus.getValue();
    this.cameraStreamStatus.next({ ...currentStatus, [cameraType]: isStreaming });
    console.log(`Updated ${cameraType} camera stream status to: ${isStreaming}`);
  }

  getCameraConnectionStatus(cameraType: 'main' | 'side'): boolean {
    return this.cameraConnectionStatus.value[cameraType];
  }

  toggleStream(cameraType: 'main' | 'side'): void {
    const isStreaming = this.getCameraStreamStatus(cameraType);
  
    // Prevent multiple clicks
    this.setCameraStreamStatus(cameraType, !isStreaming);
  
    if (isStreaming) {
      this.stopStream(cameraType);
    } else {
      this.startStream(cameraType);
    }
  }

  startStream(cameraType: 'main' | 'side'): void {
    console.log(`Starting ${cameraType} stream...`);
    this.http.get(`http://localhost:5000/start-video-stream?type=${cameraType}`).subscribe(
      () => {
        console.log(`✅ ${cameraType} camera stream started.`);
        this.setCameraStreamStatus(cameraType, true); // Update immediately
      },
      error => {
        console.error(`❌ Failed to start ${cameraType} camera stream:`, error);
        this.setCameraStreamStatus(cameraType, false); // Revert on failure
      }
    );
  }

  stopStream(cameraType: 'main' | 'side'): void {
    console.log(`Stopping ${cameraType} stream...`);
    this.http.post(`http://localhost:5000/stop-video-stream?type=${cameraType}`, {}).subscribe(
      () => {
        console.log(`✅ ${cameraType} camera stream stopped.`);
        this.setCameraStreamStatus(cameraType, false); // Update immediately
      },
      error => {
        console.error(`❌ Failed to stop ${cameraType} camera stream:`, error);
        this.setCameraStreamStatus(cameraType, true); // Revert on failure
      }
    );
  }

  // ✅ Toggle Camera Connection
  toggleConnection(cameraType: 'main' | 'side'): void {
    const isConnected = this.getCameraConnectionStatus(cameraType);

    if (isConnected) {
      this.disconnectCamera(cameraType);
    } else {
      this.connectCamera(cameraType);
    }
  }

  connectCamera(cameraType: 'main' | 'side'): void {
    this.http.post(`http://localhost:5000/connect-camera?type=${cameraType}`, {}).subscribe(
      () => {
        this.setCameraConnectionStatus(cameraType, true);
        console.log(`Connected ${cameraType} camera.`);
      },
      error => {
        console.error(`Failed to connect ${cameraType} camera:`, error);
      }
    );
  }

  disconnectCamera(cameraType: 'main' | 'side'): void {
    this.http.post(`http://localhost:5000/disconnect-camera?type=${cameraType}`, {}).subscribe(
      () => {
        this.setCameraConnectionStatus(cameraType, false);
        console.log(`Disconnected ${cameraType} camera.`);
      },
      error => {
        console.error(`Failed to disconnect ${cameraType} camera:`, error);
      }
    );
  }

  getCameraStreamStatus(cameraType: 'main' | 'side'): boolean {
    return this.cameraStreamStatus.value[cameraType];
  }

}
