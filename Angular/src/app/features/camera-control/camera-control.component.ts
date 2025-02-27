import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { SharedService } from '../../shared.service';
import { interval } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

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
  standalone: true,
  selector: 'app-camera-control',
  templateUrl: './camera-control.component.html',
  styleUrls: ['./camera-control.component.css'],
  imports: [CommonModule, FormsModule, MatIconModule]
})
export class CameraControlComponent implements OnInit {
  mainCameraSettings: CameraSettings = {} as CameraSettings;
  sideCameraSettings: CameraSettings = {} as CameraSettings;

  loadedFileName: string = '';
  saveDirectory: string = 'C:\\Users\\Public\\Pictures';

  isMainConnected: boolean = false;
  isSideConnected: boolean = false;
  isMainStreaming: boolean = false;
  isSideStreaming: boolean = false;

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


  sizeLimits: { [key: string]: number } = {
    class1: 5,
    class2: 95
  };

  private readonly BASE_URL = 'http://localhost:5000/api';
  private settingsLoaded: boolean = false;

  constructor(private http: HttpClient, public sharedService: SharedService) {}

  ngOnInit(): void {
    if (!this.settingsLoaded) {
      this.loadCameraSettings('main');
      this.loadCameraSettings('side');
      this.settingsLoaded = true;
    }
  
    // Initial checks
    this.checkCameraStatus('main');
    this.checkCameraStatus('side');
  
    // Periodically check both connection and stream status
    interval(5000).subscribe(() => {
      this.checkCameraStatus('main');
      this.checkCameraStatus('side');
    });

    setTimeout(() => {
      this.checkCameraStatus('main');
      this.checkCameraStatus('side');
    }, 3000);
  
    // Set the shared save directory
    this.sharedService.setSaveDirectory(this.saveDirectory);
  
    // Subscribe to camera connection and streaming status
    this.sharedService.cameraConnectionStatus$.subscribe(status => {
      this.isMainConnected = status.main;
      this.isSideConnected = status.side;
      console.log(`Main Connected: ${this.isMainConnected}, Side Connected: ${this.isSideConnected}`);
    });
  
    this.sharedService.cameraStreamStatus$.subscribe(status => {
      this.isMainStreaming = status.main;
      this.isSideStreaming = status.side;
      console.log(`Main Streaming: ${this.isMainStreaming}, Side Streaming: ${this.isSideStreaming}`);
    });
  }

  checkCameraStatus(cameraType: 'main' | 'side'): void {
    this.http.get(`${this.BASE_URL}/status/camera?type=${cameraType}`).subscribe(
      (response: any) => {
        if (cameraType === 'main') {
          // Always set "isMainConnected"
          this.isMainConnected = response.connected;
          this.sharedService.setCameraConnectionStatus('main', response.connected);
  
          // If not connected, forcibly set stream to false
          if (!response.connected) {
            this.isMainStreaming = false;
            this.sharedService.setCameraStreamStatus('main', false);
          } else {
            // Conditionally sync streaming: only go from false -> true
            const frontEndStreaming = this.isMainStreaming;
            const serverStreaming = response.streaming;
            if (serverStreaming && !frontEndStreaming) {
              this.isMainStreaming = true;
              this.sharedService.setCameraStreamStatus('main', true);
            }
            // If server says "false" but front end is "true", skip overwriting
          }
        } else {
          // 'side' camera logic
          this.isSideConnected = response.connected;
          this.sharedService.setCameraConnectionStatus('side', response.connected);
  
          if (!response.connected) {
            // If physically disconnected or not enumerated
            this.isSideStreaming = false;
            this.sharedService.setCameraStreamStatus('side', false);
          } else {
            const frontEndStreaming = this.isSideStreaming;
            const serverStreaming = response.streaming;
            if (serverStreaming && !frontEndStreaming) {
              this.isSideStreaming = true;
              this.sharedService.setCameraStreamStatus('side', true);
            }
          }
        }
  
        console.log(
          `${cameraType.toUpperCase()} status - ` +
          `Connected: ${response.connected}, Streaming: ${response.streaming}`
        );
      },
      error => console.error(`Error checking ${cameraType} camera status:`, error)
    );
  }
  

  checkCameraConnection(cameraType: 'main' | 'side'): void {
    this.http.get(`${this.BASE_URL}/status/camera?type=${cameraType}`).subscribe(
      (response: any) => {
        this.sharedService.setCameraConnectionStatus(cameraType, response.connected);
      },
      error => console.error(`Error checking ${cameraType} camera status:`, error)
    );
  }

  toggleConnection(cameraType: 'main' | 'side'): void {
    if ((cameraType === 'main' && this.isMainConnected) || (cameraType === 'side' && this.isSideConnected)) {
      this.disconnectCamera(cameraType);
    } else {
      this.connectCamera(cameraType);
    }
  }

  connectCamera(cameraType: 'main' | 'side'): void {
    this.http.post(`${this.BASE_URL}/connect-camera?type=${cameraType}`, {}).subscribe(
      () => {
        this.sharedService.setCameraConnectionStatus(cameraType, true);
        console.log(`${cameraType.toUpperCase()} camera connected.`);
  
        // Fetch the settings after successful connection
        this.fetchCameraSettings(cameraType);
      },
      error => console.error(`Failed to connect ${cameraType} camera:`, error)
    );
  }

  fetchCameraSettings(cameraType: 'main' | 'side'): void {
    this.http.get(`${this.BASE_URL}/get-camera-settings?type=${cameraType}`).subscribe(
      (settings: any) => {
        if (cameraType === 'main') {
          this.mainCameraSettings = settings.camera_params;
        } else {
          this.sideCameraSettings = settings.camera_params;
        }
        console.log(`${cameraType.toUpperCase()} settings loaded:`, settings);
      },
      error => console.error(`Error loading ${cameraType} camera settings:`, error)
    );
  }

  disconnectCamera(cameraType: 'main' | 'side'): void {
    this.http.post(`${this.BASE_URL}/disconnect-camera?type=${cameraType}`, {}).subscribe(
      () => {
        this.sharedService.setCameraConnectionStatus(cameraType, false);
        console.log(`${cameraType.toUpperCase()} camera disconnected.`);
      },
      error => console.error(`Failed to disconnect ${cameraType} camera:`, error)
    );
  }

  toggleStream(cameraType: 'main' | 'side'): void {
    if ((cameraType === 'main' && this.isMainStreaming) ||
        (cameraType === 'side' && this.isSideStreaming)) {
      // If currently streaming, stop
      this.stopVideoStream(cameraType);
    } else {
      // Otherwise, start
      this.startVideoStream(cameraType);
    }
  }

  startVideoStream(cameraType: 'main' | 'side'): void {
    // Remove the infinite "blob" GET call.
    // Instead, simply update the UI streaming flag in the shared service:
    this.sharedService.setCameraStreamStatus(cameraType, true);
    console.log(`${cameraType.toUpperCase()} stream set to true in SharedService (UI only).`);
    
    // (Optional) If your backend needs a "start" signal,
    // you could do a short POST to e.g. /start-camera, but
    // DO NOT request the MJPEG as a blob.
  }


  /* startVideoStream(cameraType: 'main' | 'side'): void {
    const streamUrl = `${this.BASE_URL}/start-video-stream?type=${cameraType}&nocache=${new Date().getTime()}`;
    
    this.http.get(streamUrl, { responseType: 'blob' }).subscribe(
      () => {
        this.sharedService.setCameraStreamStatus(cameraType, true);
        console.log(`${cameraType.toUpperCase()} stream started.`);
      },
      error => console.error(`Failed to start ${cameraType} stream:`, error)
    );
  } */

  stopVideoStream(cameraType: 'main' | 'side'): void {
    this.http.post(`${this.BASE_URL}/stop-video-stream?type=${cameraType}`, {}).subscribe(
      () => {
        this.sharedService.setCameraStreamStatus(cameraType, false);
        console.log(`${cameraType.toUpperCase()} stream stopped.`);
      },
      error => console.error(`Failed to stop ${cameraType} stream:`, error)
    );
  }

  loadCameraSettings(cameraType: 'main' | 'side'): void {
    this.http.get(`${this.BASE_URL}/get-camera-settings?type=${cameraType}`).subscribe(
      (settings: any) => {
        if (cameraType === 'main') {
          this.mainCameraSettings = settings;
        } else {
          this.sideCameraSettings = settings;
        }
        console.log(`[${cameraType}] Loaded settings:`, settings);
      },
      error => console.error(`Error loading ${cameraType} camera settings:`, error)
    );
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
  
  applySetting(setting: string, cameraType: 'main' | 'side'): void {
    const value = cameraType === 'main' ? this.mainCameraSettings[setting] : this.sideCameraSettings[setting];
    console.log(`Applying setting ${setting}: ${value}`);

    this.http.post(`${this.BASE_URL}/update-camera-settings`, {
      camera_type: cameraType,
      setting_name: setting,
      setting_value: value
    }).subscribe((response: any) => {
        console.log(`Setting applied successfully for ${cameraType} camera:`, response);

        const correctedValue = response.updated_value;
        if (cameraType === 'main') {
          this.mainCameraSettings[setting] = correctedValue;
        } else {
          this.sideCameraSettings[setting] = correctedValue;
        }
      },
      error => {
        console.error(`Error applying setting for ${cameraType} camera:`, error);
      }
    );
}


applySizeLimit(limitName: 'class1' | 'class2'): void {
  let value = Number(this.sizeLimits[limitName]); // Explicitly convert to a number
  console.log(`Applying size limit ${limitName}: ${value}`);

  this.http.post(`${this.BASE_URL}/update-other-settings`, {
    category: 'size_limits',
    setting_name: limitName,
    setting_value: value  // Now it's always a number
  }).subscribe((response: any) => {
    console.log(`Size limit applied successfully:`, response);

    // Ensure we store it as a number again
    this.sizeLimits[limitName] = Number(response.updated_value);
  },
  error => {
    console.error(`Error applying size limit ${limitName}:`, error);
  });
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

