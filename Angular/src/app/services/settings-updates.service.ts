import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface SizeLimits {
  class1: number;
  class2: number;
  ng_limit: number;
}

export interface SaveSettings {
  save_csv: boolean;
  save_images: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class SettingsUpdatesService {
  // Initialize with default/fallback values. These may be overwritten by the backend.
  private sizeLimitsSubject = new BehaviorSubject<SizeLimits>({
    class1: 5,
    class2: 95,
    ng_limit: 15
  });

  private saveSettingsSubject = new BehaviorSubject<SaveSettings>({
    save_csv: false,
    save_images: false
  });
  
  // Expose the observable for components to subscribe to.
  sizeLimits$ = this.sizeLimitsSubject.asObservable();
  saveSettings$ = this.saveSettingsSubject.asObservable();

  // Call this method to update the current size limits.
  updateSizeLimits(newLimits: SizeLimits): void {
    this.sizeLimitsSubject.next(newLimits);
  }

  updateSaveSettings(newSettings: SaveSettings): void {
    this.saveSettingsSubject.next(newSettings);
  }
}
