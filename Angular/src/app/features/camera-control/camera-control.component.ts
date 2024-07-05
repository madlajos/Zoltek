import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

interface CameraSettings {
  Width: number;
  Height: number;
  OffsetX: number;
  OffsetY: number;
  ExposureTime: number;
  Gain: number;
  Gamma: number;
  FrameRate: number;
  [key: string]: any; // Add index signature to allow dynamic property access
}

@Component({
  selector: 'app-camera-control',
  templateUrl: './camera-control.component.html',
  styleUrls: ['./camera-control.component.css']
})
export class CameraControlComponent implements OnInit {
  cameraSettings: CameraSettings = {
    Width: 800,
    Height: 400,
    OffsetX: 0,
    OffsetY: 0,
    ExposureTime: 200,
    Gain: 10,
    Gamma: 100,
    FrameRate: 30
  };

  // Define the desired order of the settings
  settingOrder: string[] = [
    'Width',
    'Height',
    'OffsetX',
    'OffsetY',
    'ExposureTime',
    'Gain',
    'Gamma',
    'FrameRate'
  ];

  private readonly BASE_URL = 'http://localhost:5000/api';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadCameraSettings();
  }

  loadCameraSettings(): void {
    this.http.get('/assets/settings.json').subscribe((settings: any) => {
      this.cameraSettings = settings.camera_params;
      console.log('Camera settings loaded:', this.cameraSettings);
    });
  }

  applySetting(setting: string): void {
    const value = this.cameraSettings[setting];
    console.log(`Applying setting ${setting}: ${value}`);
    // Add actual implementation to apply the individual setting to the camera
    this.http.post('/api/update-camera-settings', { [setting]: value }).subscribe(response => {
      console.log('Setting applied successfully:', response);
    }, error => {
      console.error('Error applying setting:', error);
    });
  }

  handleKeyDown(event: KeyboardEvent, setting: string): void {
    if (event.key === 'Enter') {
      console.log(`Enter pressed for ${setting}`);
      this.applySetting(setting);
    }
  }

  objectKeys(obj: any): string[] {
    return Object.keys(obj);
  }
}
