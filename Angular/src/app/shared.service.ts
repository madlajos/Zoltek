import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class SharedService {
  private selectedImageSource = new BehaviorSubject<string | null>(null);
  selectedImage$ = this.selectedImageSource.asObservable();

  // ✅ Track main and side camera connection status
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

  private saveDirectory: string = '';

  // ✅ Set selected image
  setSelectedImage(imagePath: string | null): void {
    this.selectedImageSource.next(imagePath);
  }

  // ✅ Set save directory
  setSaveDirectory(directory: string): void {
    this.saveDirectory = directory;
    console.log(`Save directory set to: ${directory}`);
  }

  getSaveDirectory(): string {
    console.log(`Retrieving save directory: ${this.saveDirectory}`);
    return this.saveDirectory;
  }

  // ✅ Unified method to set camera connection status
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

  // ✅ Helper: Get the current status for specific camera
  getCameraConnectionStatus(cameraType: 'main' | 'side'): boolean {
    return this.cameraConnectionStatus.value[cameraType];
  }
}
