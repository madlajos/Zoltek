import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class SharedService {
  private selectedImageSource = new BehaviorSubject<string | null>(null);
  selectedImage$ = this.selectedImageSource.asObservable();

  private cameraConnectionStatus = new BehaviorSubject<boolean>(false);
  cameraConnectionStatus$ = this.cameraConnectionStatus.asObservable();

  setSelectedImage(imagePath: string | null): void {
    this.selectedImageSource.next(imagePath);
  }

  private saveDirectory: string = '';

  setSaveDirectory(directory: string): void {
    this.saveDirectory = directory;
    console.log(`Save directory set to: ${directory}`);
  }

  getSaveDirectory(): string {
    console.log(`Retrieving save directory: ${this.saveDirectory}`);
    return this.saveDirectory;
  }

  setCameraConnectionStatus(status: boolean) {
    this.cameraConnectionStatus.next(status);
  }
}
