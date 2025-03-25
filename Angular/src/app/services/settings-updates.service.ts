import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface SizeLimits {
  class1: number;
  class2: number;
  ng_limit: number;
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
  
  // Expose the observable for components to subscribe to.
  sizeLimits$ = this.sizeLimitsSubject.asObservable();

  // Call this method to update the current size limits.
  updateSizeLimits(newLimits: SizeLimits): void {
    this.sizeLimitsSubject.next(newLimits);
  }
}
