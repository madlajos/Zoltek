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

  loadedFileName: string = '';

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
      this.loadedFileName = 'settings.json'.replace('.json', '');
      console.log('Camera settings loaded:', this.cameraSettings);
    });
  }

  saveSettings(): void {
    console.log('Save Settings button clicked');
    const settings = {
      camera_params: this.cameraSettings
    };
    this.http.post(`${this.BASE_URL}/save-camera-settings`, settings).subscribe(response => {
      console.log('Settings saved successfully:', response);
    }, error => {
      console.error('Error saving settings:', error);
    });
  }

  loadSettings(): void {
    console.log('Load Settings button clicked');
    this.http.get(`${this.BASE_URL}/load-camera-settings`).subscribe((settings: any) => {
      this.cameraSettings = settings.camera_params;
      this.loadedFileName = settings.fileName.replace('.json', '');
      console.log('Loaded settings:', this.cameraSettings);
    }, error => {
      console.error('Error loading settings:', error);
    });
  }

  applySetting(setting: string): void {
    const value = this.cameraSettings[setting];
    console.log(`Applying setting ${setting}: ${value}`);
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
