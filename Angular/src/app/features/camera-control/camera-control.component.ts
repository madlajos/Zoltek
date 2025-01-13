import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { SharedService } from '../../shared.service';
import { interval } from 'rxjs';

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
  mainCameraSettings: CameraSettings = {
    Width: 800,
    Height: 400,
    OffsetX: 0,
    OffsetY: 0,
    ExposureTime: 200,
    Gain: 10,
    Gamma: 100,
    FrameRate: 30
  };

  sideCameraSettings: CameraSettings = {
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
  saveDirectory: string = 'C:\\Users\\Public\\Pictures';
  isMainConnected: boolean = false;
  isSideConnected: boolean = false;

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

  constructor(private http: HttpClient, public sharedService: SharedService) {}

  ngOnInit(): void {
    // Load settings for both cameras
    this.loadCameraSettings('main');
    this.loadCameraSettings('side');
  
    // Set the shared save directory
    this.sharedService.setSaveDirectory(this.saveDirectory);
  
    // Subscribe to connection status for both cameras
    this.sharedService.cameraConnectionStatus$.subscribe((status: { main: boolean; side: boolean }) => {
      this.isMainConnected = status.main;
      this.isSideConnected = status.side;

      console.log(`Main Connected: ${this.isMainConnected}, Side Connected: ${this.isSideConnected}`);
    });
    

    
    
    // Periodically check connection status for both cameras
    interval(5000).subscribe(() => {
      this.checkCameraConnection('main');
      this.checkCameraConnection('side');
    });
  }


  checkCameraConnection(cameraType: 'main' | 'side'): void {
    this.http.get(`${this.BASE_URL}/status/camera?type=${cameraType}`).subscribe((status: any) => {
      this.sharedService.setCameraConnectionStatus(cameraType, status.connected);
    }, error => {
      console.error(`Error checking ${cameraType} camera connection status:`, error);
    });
  }

  loadCameraSettings(cameraType: 'main' | 'side'): void {
    this.http.get(`/assets/settings_${cameraType}.json`).subscribe((settings: any) => {
      if (cameraType === 'main') {
        this.mainCameraSettings = settings.camera_params;
        console.log('Main camera settings loaded:', this.mainCameraSettings);
      } else {
        this.sideCameraSettings = settings.camera_params;
        console.log('Side camera settings loaded:', this.sideCameraSettings);
      }
    }, error => {
      console.error(`Error loading ${cameraType} camera settings:`, error);
    });
  }
  

  saveSettings(cameraType: 'main' | 'side'): void {
    console.log(`Save Settings button clicked for ${cameraType} camera`);
  
    const settings = {
      camera_params: cameraType === 'main' ? this.mainCameraSettings : this.sideCameraSettings
    };
  
    this.http.post(`${this.BASE_URL}/save-camera-settings?type=${cameraType}`, settings).subscribe(
      (response: any) => {
        console.log(`Settings for ${cameraType} camera saved successfully:`, response);
        this.updateCameraSettingsOnInterface(response.updated_settings, cameraType); // Update the correct interface
      },
      error => {
        console.error(`Error saving settings for ${cameraType} camera:`, error);
      }
    );
  }
  
  //Placeholder
  loadSettings(cameraType: 'main' | 'side'): void {
    this.http.get(`${this.BASE_URL}/load-camera-settings?type=${cameraType}`).subscribe((settings: any) => {
      if (cameraType === 'main') {
        this.mainCameraSettings = settings.camera_params;
      } else {
        this.sideCameraSettings = settings.camera_params;
      }
    });
  }



  selectSaveDirectory(): void {
    this.http.get('http://localhost:5000/select-folder').subscribe(
      (response: any) => {
        if (response.folder) {
          this.saveDirectory = response.folder;
          this.sharedService.setSaveDirectory(response.folder);
        } else {
          console.error('No folder selected');
        }
      },
      error => {
        console.error('Failed to select folder:', error);
      }
    );
  }

  applySetting(setting: string, cameraType: 'main' | 'side'): void {
    const value = cameraType === 'main' ? this.mainCameraSettings[setting] : this.sideCameraSettings[setting];
    console.log(`Applying setting ${setting}: ${value}`);

    this.http.post(`${this.BASE_URL}/update-camera-settings`, {
      camera_type: cameraType,
      setting_name: setting,
      setting_value: value
    }).subscribe(
      (response: any) => {
        console.log(`Setting applied successfully for ${cameraType} camera:`, response);
      },
      error => {
        console.error(`Error applying setting for ${cameraType} camera:`, error);
      }
    );
}


  handleKeyDown(event: KeyboardEvent, setting: string, cameraType: 'main' | 'side'): void {
    if (event.key === 'Enter') {
      console.log(`Enter pressed for ${setting} on ${cameraType} camera`);
      this.applySetting(setting, cameraType);  // Pass both arguments
    }
  }
  

  validateInput(event: any, setting: string, cameraType: 'main' | 'side'): void {
    const input = event.target.value.replace(/[^0-9.]/g, '');
    if (cameraType === 'main') {
      this.mainCameraSettings[setting] = input;
    } else {
      this.sideCameraSettings[setting] = input;
    }
  }

  preventInvalidChars(event: KeyboardEvent, setting: string): void {
    const char = String.fromCharCode(event.which);
    const pattern = ['Width', 'Height', 'OffsetX', 'OffsetY', 'ExposureTime'].includes(setting) ? 
                    /[0-9]/ : /[0-9.]/;
    if (!pattern.test(char)) {
      event.preventDefault();
    }
  }

  objectKeys(obj: any): string[] {
    return Object.keys(obj);
  }

  updateCameraSettingsOnInterface(updatedSettings: any, cameraType: 'main' | 'side'): void {
    const targetSettings = cameraType === 'main' ? this.mainCameraSettings : this.sideCameraSettings;
    
    for (const key in updatedSettings) {
      if (updatedSettings.hasOwnProperty(key)) {
        targetSettings[key] = updatedSettings[key];
      }
    }
  }
  

  center(axis: 'X' | 'Y', cameraType: 'main' | 'side'): void {
    this.http.post(`${this.BASE_URL}/set-centered-offset?type=${cameraType}`, {}).subscribe((response: any) => {
      if (cameraType === 'main') {
        this.mainCameraSettings[`Offset${axis}`] = response[`Offset${axis}`];
      } else {
        this.sideCameraSettings[`Offset${axis}`] = response[`Offset${axis}`];
      }
    });
  }

}

