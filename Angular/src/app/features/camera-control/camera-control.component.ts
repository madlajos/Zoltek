import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { SharedService } from '../../shared.service';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { interval, Subscription, switchMap, catchError, of, timeout  } from 'rxjs';
import { ErrorNotificationService } from '../../services/error-notification.service';
import { SettingsUpdatesService, SizeLimits, SaveSettings, CameraSettings } from '../../services/settings-updates.service';

@Component({
  standalone: true,
  selector: 'app-camera-control',
  templateUrl: './camera-control.component.html',
  styleUrls: ['./camera-control.component.css'],
  imports: [CommonModule, FormsModule, MatIconModule]
})

export class CameraControlComponent implements OnInit, OnDestroy {
  mainCameraSettings: CameraSettings = { 
    Width: 4200, Height: 2160, OffsetX: 0, OffsetY: 0,
    ExposureTime: 20000, Gain: 0, Gamma: 1, FrameRate: 20 
  };
  sideCameraSettings: CameraSettings = { 
    Width: 4200, Height: 2160, OffsetX: 0, OffsetY: 0,
    ExposureTime: 20000, Gain: 0, Gamma: 1, FrameRate: 20
  };
  
  unifiedPollingSub!: Subscription;

  private settingsLoaded: boolean = false;
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

  // Changed: Use the SizeLimits interface instead of a generic object.
  sizeLimits: SizeLimits = {
    class1: 5,
    class2: 95,
    ng_limit: 15
  };

  saveSettings: SaveSettings = {
    save_csv: false,
    save_images: false
  };
  
  connectionPollingMain: Subscription | undefined;
  connectionPollingSide: Subscription | undefined;
  reconnectionPollingMain: Subscription | undefined;
  reconnectionPollingSide: Subscription | undefined;

  isMainConnected: boolean = false;
  isSideConnected: boolean = false;
  isMainStreaming: boolean = false;
  isSideStreaming: boolean = false;

  measurementActive: boolean = false;
  private measurementActiveSub!: Subscription;

  loadedFileName: string = '';
  saveDirectory: string = 'C:\\Users\\Public\\Pictures';

  private readonly MAIN_CAMERA_ERR_CODE = "E1111";
  private readonly SIDE_CAMERA_ERR_CODE = "E1121";

  private readonly BASE_URL = 'http://localhost:5000/api';

  constructor(private http: HttpClient,
    public sharedService: SharedService,
    private errorNotificationService: ErrorNotificationService,
    private settingsUpdatesService: SettingsUpdatesService
  ) { }

  ngOnInit(): void {
    // First, delay the initial loading of camera settings.
    // (This can be adjusted if needed.)
    if (!this.settingsLoaded) {
      setTimeout(() => {
        this.loadCameraSettings('main');
        this.loadCameraSettings('side');
        this.settingsLoaded = true;
      }, 5000);
    }
  
    // Unified polling: poll the main camera settings every 500 ms until the width is nonzero.
    this.unifiedPollingSub = interval(500).pipe(
      switchMap(() =>
        this.http.get<CameraSettings>(`${this.BASE_URL}/get-camera-settings?type=main`)
          .pipe(
            catchError(error => {
              console.error('Error polling main camera settings:', error);
              // Return a default object so the polling keeps going.
              return of({ Width: 0, Height: 0, OffsetX: 0, OffsetY: 0, ExposureTime: 0, Gain: 0, Gamma: 0, FrameRate: 0 });
            })
          )
      )
    ).subscribe(settings => {
      console.log(`[Unified Polling] Main camera Width = ${settings.Width}`);
      // Check if the main camera settings are valid (e.g., Width is not 0)
      if (settings && settings.Width !== 0) {
        // Once valid, update all groups.
        this.loadCameraSettings('main');
        this.loadCameraSettings('side');
        this.loadOtherSettings();
  
        // Start checking camera status and connection polling now that the backend is up.
        this.checkCameraStatus('main');
        this.checkCameraStatus('side');
        this.startConnectionPolling('main');
        this.startConnectionPolling('side');
  
        // Unsubscribe from unified polling so these calls are no longer repeated.
        this.unifiedPollingSub.unsubscribe();
      }
    });
  
    // Set the shared save directory.
    this.sharedService.setSaveDirectory(this.saveDirectory);
  
    // Subscribe to shared observables.
    this.measurementActiveSub = this.sharedService.measurementActive$.subscribe(active => {
      this.measurementActive = active;
    });
  
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
  
    // Delay the GET calls for other settings (size limits, save settings) as well.
    setTimeout(() => {
      this.http.get<{ size_limits: SizeLimits }>(`${this.BASE_URL}/get-other-settings?category=size_limits`)
        .subscribe({
          next: response => {
            if (response && response.size_limits) {
              this.sizeLimits = response.size_limits;
              this.settingsUpdatesService.updateSizeLimits(this.sizeLimits);
              console.log("Loaded size limits from backend:", this.sizeLimits);
            }
          },
          error: error => {
            console.error("Error loading size limits from backend:", error);
          }
        });
  
      this.http.get<{ save_settings: SaveSettings }>(`${this.BASE_URL}/get-other-settings?category=save_settings`)
        .subscribe({
          next: response => {
            if (response && response.save_settings) {
              this.saveSettings = response.save_settings;
              this.settingsUpdatesService.updateSaveSettings(this.saveSettings);
              console.log("Loaded Save Settings from backend:");
            }
          },
          error: error => {
            console.error("Error loading Save Settings from backend:", error);
          }
        });
    }, 5000);
  }

  ngOnDestroy(): void {
    this.stopConnectionPolling('main');
    this.stopConnectionPolling('side');
    this.stopReconnectionPolling('main');
    this.stopReconnectionPolling('side');

    if (this.unifiedPollingSub) {
      this.unifiedPollingSub.unsubscribe();
    }

    if (this.measurementActiveSub) {
      this.measurementActiveSub.unsubscribe();
    }
  }

  loadOtherSettings(): void {
    this.http.get<{ size_limits: SizeLimits }>(`${this.BASE_URL}/get-other-settings?category=size_limits`)
      .subscribe({
        next: response => {
          if (response && response.size_limits) {
            this.sizeLimits = response.size_limits;
            this.settingsUpdatesService.updateSizeLimits(this.sizeLimits);
            console.log("Loaded size limits from backend:", this.sizeLimits);
          }
        },
        error: error => {
          console.error("Error loading size limits from backend:", error);
        }
      });

    this.http.get<{ save_settings: SaveSettings }>(`${this.BASE_URL}/get-other-settings?category=save_settings`)
      .subscribe({
        next: response => {
          if (response && response.save_settings) {
            this.saveSettings = response.save_settings;
            this.settingsUpdatesService.updateSaveSettings(this.saveSettings);
            console.log("Loaded save settings from backend:", this.saveSettings);
          }
        },
        error: error => {
          console.error("Error loading save settings from backend:", error);
        }
      });
  }

  checkCameraStatus(cameraType: 'main' | 'side'): void {
    this.http.get<{ connected: boolean; streaming?: boolean }>(`${this.BASE_URL}/status/camera?type=${cameraType}`)
      .pipe(
        // Fail if no response within 3000ms
        timeout(3000),
        // On error, catch it and return a default disconnected response.
        catchError(err => {
          console.error(`Error checking ${cameraType} camera status:`, err);
          return of({ connected: false, streaming: false });
        })
      )
      .subscribe({
        next: (response) => {
          if (response.connected) {
            this.sharedService.setCameraConnectionStatus(cameraType, true);
            // Remove any existing error for this camera.
            const errCode = cameraType === 'main' ? this.MAIN_CAMERA_ERR_CODE : this.SIDE_CAMERA_ERR_CODE;
            this.errorNotificationService.removeError(errCode);
            // Stop any reconnection polling and resume normal polling.
            this.stopReconnectionPolling(cameraType);
            this.startConnectionPolling(cameraType);
            // If streaming is not active, start streaming.
            if (cameraType === 'main' && !this.isMainStreaming) {
              console.log("Main camera connected but not streaming. Starting stream...");
              this.startVideoStream('main');
            } else if (cameraType === 'side' && !this.isSideStreaming) {
              console.log("Side camera connected but not streaming. Starting stream...");
              this.startVideoStream('side');
            }
          } else {
            // Camera not connected, update both connection and stream status.
            this.sharedService.setCameraConnectionStatus(cameraType, false);
            this.sharedService.setCameraStreamStatus(cameraType, false);
            this.stopConnectionPolling(cameraType);
            this.startReconnectionPolling(cameraType);
          }
          console.log(`${cameraType.toUpperCase()} status - Connected: ${response.connected}, Streaming: ${response.streaming}`);
        },
        error: (err) => {
          // This error block should rarely fire because catchError handles timeouts.
          console.error(`Unexpected error checking ${cameraType} camera status:`, err);
          this.sharedService.setCameraConnectionStatus(cameraType, false);
          this.sharedService.setCameraStreamStatus(cameraType, false);
          this.stopConnectionPolling(cameraType);
          this.startReconnectionPolling(cameraType);
        }
      });
  }

  
  
  
  startConnectionPolling(cameraType: 'main' | 'side'): void {
    if (cameraType === 'main' && !this.connectionPollingMain) {
      this.connectionPollingMain = interval(5000).subscribe(() => {
        this.checkCameraStatus('main');
      });
    } else if (cameraType === 'side' && !this.connectionPollingSide) {
      this.connectionPollingSide = interval(5000).subscribe(() => {
        this.checkCameraStatus('side');
      });
    }
  }
  
  stopConnectionPolling(cameraType: 'main' | 'side'): void {
    if (cameraType === 'main') {
      this.connectionPollingMain?.unsubscribe();
      this.connectionPollingMain = undefined;
    } else {
      this.connectionPollingSide?.unsubscribe();
      this.connectionPollingSide = undefined;
    }
  }
  
  startReconnectionPolling(cameraType: 'main' | 'side'): void {
    if (cameraType === 'main' && !this.reconnectionPollingMain) {
      this.reconnectionPollingMain = interval(3000).subscribe(() => {
        this.tryReconnectCamera('main');
      });
    } else if (cameraType === 'side' && !this.reconnectionPollingSide) {
      this.reconnectionPollingSide = interval(3000).subscribe(() => {
        this.tryReconnectCamera('side');
      });
    }
  }
  
  stopReconnectionPolling(cameraType: 'main' | 'side'): void {
    if (cameraType === 'main') {
      this.reconnectionPollingMain?.unsubscribe();
      this.reconnectionPollingMain = undefined;
    } else {
      this.reconnectionPollingSide?.unsubscribe();
      this.reconnectionPollingSide = undefined;
    }
  }

  tryReconnectCamera(cameraType: 'main' | 'side'): void {
    this.http.post(`${this.BASE_URL}/connect-camera?type=${cameraType}`, {})
      .subscribe({
        next: (response: any) => {
          console.info(`${cameraType.toUpperCase()} camera reconnected:`, response.message);
          this.sharedService.setCameraConnectionStatus(cameraType, true);
          const errCode = cameraType === 'main' ? this.MAIN_CAMERA_ERR_CODE : this.SIDE_CAMERA_ERR_CODE;
          this.errorNotificationService.removeError(errCode);
          this.stopReconnectionPolling(cameraType);
          this.startConnectionPolling(cameraType);
        },
        error: (error) => {
          console.warn(`${cameraType.toUpperCase()} camera reconnection attempt failed.`, error);
        }
      });
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
      (response: any) => {
        this.sharedService.setCameraConnectionStatus(cameraType, true);
        this.errorNotificationService.removeError(`${cameraType} camera disconnected`);
        console.log(`${cameraType.toUpperCase()} camera connected.`);
        // Optionally trigger a status refresh:
        this.checkCameraStatus(cameraType);
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
      (response: any) => {
        this.sharedService.setCameraConnectionStatus(cameraType, false);
        console.log(`${cameraType.toUpperCase()} camera disconnected.`);
        this.checkCameraStatus(cameraType);
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
    this.sharedService.setCameraStreamStatus(cameraType, true);
    console.log(`${cameraType.toUpperCase()} stream set to true in SharedService (UI only).`);
  }

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
    this.http.get<CameraSettings>(`${this.BASE_URL}/get-camera-settings?type=${cameraType}`)
      .subscribe({
        next: (settings: CameraSettings) => {
          if (cameraType === 'main') {
            this.mainCameraSettings = settings;
            this.settingsUpdatesService.updateMainCameraSettings(settings);
            console.log(`Loaded main camera settings:`, settings);
          } else {
            this.sideCameraSettings = settings;
            this.settingsUpdatesService.updateSideCameraSettings(settings);
            console.log(`Loaded side camera settings:`, settings);
          }
        },
        error: error => console.error(`Error loading ${cameraType} camera settings:`, error)
      });
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

  applySizeLimit(limitName: 'class1' | 'class2' | 'ng_limit'): void {
    let value = Number(this.sizeLimits[limitName]); // convert to number explicitly
    console.log(`Applying size limit ${limitName}: ${value}`);

    this.http.post(`${this.BASE_URL}/update-other-settings`, {
      category: 'size_limits',
      setting_name: limitName,
      setting_value: value
    }).subscribe({
      next: (response: any) => {
        console.log(`Size limit applied successfully:`, response);
        // Update the local value with the response.
        this.sizeLimits[limitName] = Number(response.updated_value);
        
        // Optionally, reload all size limits from backend.
        this.http.get<{ size_limits: SizeLimits }>(`${this.BASE_URL}/get-other-settings?category=size_limits`)
          .subscribe({
            next: resp => {
              if (resp && resp.size_limits) {
                this.sizeLimits = resp.size_limits;
                console.log("Reloaded size limits:", this.sizeLimits);
                // Publish the updated limits to the shared service.
                this.settingsUpdatesService.updateSizeLimits(this.sizeLimits);
              }
            },
            error: err => console.error("Error reloading settings:", err)
          });
      },
      error: error => {
        console.error(`Error applying size limit ${limitName}:`, error);
      }
    });
  }

  applySaveSetting(settingName: 'save_csv' | 'save_images'): void {
    let value = Boolean(this.saveSettings[settingName]); // convert to number explicitly
    console.log(`Applying save setting: ${settingName}to ${value}`);

    this.http.post(`${this.BASE_URL}/update-other-settings`, {
      category: 'save_settings',
      setting_name: settingName,
      setting_value: value
    }).subscribe({
      next: (response: any) => {
        console.log(`Save settings applied successfully:`, response);
        // Update the local value with the response.
        this.saveSettings[settingName] = Boolean(response.updated_value);
        this.settingsUpdatesService.updateSaveSettings(this.saveSettings);

      },
      error: error => {
        console.error(`Error save setting: ${settingName}:`, error);
      }
    });
  }

  handleKeyDown(event: KeyboardEvent, setting: string, cameraType: 'main' | 'side'): void {
    if (event.key === 'Enter') {
      console.log(`Enter pressed for ${setting} on ${cameraType} camera`);
      this.applySetting(setting, cameraType);
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
}
