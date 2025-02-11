import { Component, OnInit, ViewChild, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { TurntableControlComponent } from '../turntable-control/turntable-control.component';
import { Observable } from 'rxjs';
import { switchMap, tap, finalize } from 'rxjs/operators';

@Component({
  selector: 'app-control-panel',
  templateUrl: './control-panel.component.html',
  styleUrls: ['./control-panel.component.css']
})
export class ControlPanelComponent implements OnInit {
  private readonly BASE_URL = 'http://localhost:5000';

  relayState: boolean = false;
  nozzleId: string = "";
  measurementActive: boolean = false;

  currentMeasurement: number = 0;
  totalMeasurements: number = 18;
  turntablePosition: number | string = '?';

  // Add ViewChild reference to access TurntableControlComponent
  @ViewChild(TurntableControlComponent) turntableControl!: TurntableControlComponent;

  get progressPercentage(): number {
    return (this.currentMeasurement / this.totalMeasurements) * 100;
  }

  results: { label: string, value: number }[] = [
    { label: 'Result 1', value: 0 },
    { label: 'Result 2', value: 0 },
    { label: 'Result 3', value: 0 }
  ];

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    setInterval(() => {
      this.fetchBarcodeData();
    }, 1000); // Fetch barcode every 1 second
  }

  ngAfterViewInit(): void {
    if (!this.turntableControl) {
      console.error("TurntableControlComponent is not available!");
    }
  }

  // Toggle Relay Function (unchanged)
  toggleRelay(): void {
    this.relayState = !this.relayState;
    const payload = { state: this.relayState ? 1 : 0 };
    this.http.post(`${this.BASE_URL}/toggle-relay`, payload).subscribe(
      (response: any) => {
        console.log(`Relay ${this.relayState ? 'ON' : 'OFF'}`, response);
      },
      (error) => {
        console.error('Error toggling relay:', error);
        this.relayState = !this.relayState;
      }
    );
  }

  // Rotate Up/Down Functions (unchanged)
  moveTurntable(degrees: number): void {
    this.http.post(`${this.BASE_URL}/move_turntable_relative`, { degrees }).subscribe(
      () => console.log(`Turntable moved ${degrees} degrees`),
      error => console.error(`Error moving turntable by ${degrees}°:`, error)
    );
  }

  homeTurntable(): void {
    if (this.turntableControl) {
      this.turntableControl.homeTurntable();
      this.turntablePosition = this.turntableControl.turntablePosition; // Fetch position
    } else {
      console.error("TurntableControlComponent is not available.");
    }
  }


  toggleMeasurement(): void {
    this.measurementActive = !this.measurementActive;

    if (this.measurementActive) {
      console.log("Measurement cycle started.");
      this.startMeasurement();
    } else {
      console.log("Measurement cycle stopping...");
      this.stopMeasurement();
    }
  }

  stopMeasurement(): void {
    this.measurementActive = false;
    this.currentMeasurement = 0;
    this.results = this.results.map(res => ({ ...res, value: 0 }));
    console.log("Results cleared, progress bar reset.");

    if (this.relayState) this.toggleRelay();
  }

  fetchBarcodeData(): void {
    this.http.get<{ barcode: string }>(`${this.BASE_URL}/api/get-barcode`).subscribe(
      (response) => {
        console.log("Barcode received from API:", response.barcode);
        this.nozzleId = response.barcode; // Update UI
      },
      (error) => {
        console.error("Failed to fetch barcode!", error);
      }
    );
  }
  
  startMeasurement(): void {
    console.log("Starting measurement cycle...");

    const startProcess = () => this.http.post(`${this.BASE_URL}/home_turntable_with_image`, {}).pipe(
      tap(() => console.log("Turntable homed successfully")),
      switchMap(() => this.waitForTurntableDone()),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_center_circle`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_center_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_outer_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/update_results`, {})),
      tap((response: any) => this.updateResultsUI(response)),
      finalize(() => this.performMeasurementCycle())
    );

    if (!this.relayState) {
        this.toggleRelay();
        setTimeout(() => startProcess().subscribe(), 500);  // ✅ **Now it correctly starts**
    } else {
        startProcess().subscribe();  // ✅ **Now it runs immediately if the relay is already on**
    }
}


  

  performMeasurementCycle(): void {
    if (!this.measurementActive || this.currentMeasurement >= this.totalMeasurements) {
      console.log("Measurement cycle completed.");
      return;
    }

    console.log(`Starting measurement ${this.currentMeasurement + 1} of ${this.totalMeasurements}...`);

    this.http.post(`${this.BASE_URL}/move_turntable_relative`, { degrees: 20 }).pipe(
      tap(() => console.log("Turntable rotated 20°")),
      switchMap(() => this.waitForTurntableDone()),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_center_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_outer_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/update_results`, {})),
      tap((response: any) => this.updateResultsUI(response)),
      finalize(() => {
        this.currentMeasurement++;
        this.performMeasurementCycle();
      })
    ).subscribe();
  }
  

  waitForTurntableDone(): Observable<any> {
    return new Observable(observer => {
      const checkStatus = () => {
        this.http.get<{ connected: boolean; port?: string }>(`${this.BASE_URL}/api/status/serial/turntable`).subscribe(
          statusResponse => {
            if (statusResponse.connected) {
              console.log("Turntable movement completed.");
              observer.next();
              observer.complete();
            } else {
              setTimeout(checkStatus, 500);
            }
          },
          error => {
            console.error("Error checking turntable status!", error);
            setTimeout(checkStatus, 500);
          }
        );
      };
      checkStatus();
    });
  }

  updateResultsUI(response: any): void {
    if (this.measurementActive && response?.result_counts) {
      this.results = response.result_counts.map((count: number, index: number) => ({
        label: `Result ${index + 1}`,
        value: count
      }));
      this.cdr.detectChanges();  // Ensure UI updates
    }
  }
}
