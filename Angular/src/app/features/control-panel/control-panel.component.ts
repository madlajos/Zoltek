import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewChild, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { TurntableControlComponent } from '../turntable-control/turntable-control.component';
import { Observable } from 'rxjs';
import { switchMap, tap, finalize } from 'rxjs/operators';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { SharedService, MeasurementResult } from '../../shared.service';

@Component({
  standalone: true,
  selector: 'app-control-panel',
  templateUrl: './control-panel.component.html',
  styleUrls: ['./control-panel.component.css'],
  imports: [CommonModule, FormsModule, MatIconModule, TurntableControlComponent]
})
export class ControlPanelComponent implements OnInit {
  private readonly BASE_URL = 'http://localhost:5000/api';

  relayState: boolean = false;
  nozzleId: string = "";
  measurementActive: boolean = false;

  currentMeasurement: number = 0;
  totalMeasurements: number = 18;
  turntablePosition: number | string = '?';

  @ViewChild(TurntableControlComponent) turntableControl!: TurntableControlComponent;

  get progressPercentage(): number {
    return (this.currentMeasurement / this.totalMeasurements) * 100;
  }

  results: { label: string, value: number }[] = [
    { label: 'Eldugult', value: 0 },
    { label: 'Részl. Eldugult', value: 0 },
    { label: 'Tiszta', value: 0 }
  ];

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef, private sharedService: SharedService) {}

  ngOnInit(): void {
    setInterval(() => {
      this.fetchBarcodeData();
    }, 3000);

    this.sharedService.measurementResults$.subscribe((res) => {
      this.results = res;
      this.cdr.detectChanges();
    });
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
    
    // Reset only the values while keeping the original labels
    this.results = this.results.map(res => ({ ...res, value: 0 }));
    
    console.log("Results cleared, progress bar reset.");

    this.http.post(`${this.BASE_URL}/reset_results`, {}).subscribe(
        (response: any) => {
            console.log("Backend results reset:", response);
            
            if (response?.result_counts && this.results.length === response.result_counts.length) {
                // Update values while retaining the original labels
                this.results.forEach((result, index) => {
                    result.value = response.result_counts[index];
                });
            }
        },
        (error) => {
            console.error("Failed to reset backend results:", error);
        }
    );
}

  fetchBarcodeData(): void {
    this.http.get<{ barcode: string }>(`${this.BASE_URL}/get-barcode`).subscribe(
      (response) => {
        console.log("Barcode received from API:", response.barcode);
        this.nozzleId = response.barcode;
      },
      (error) => {
        console.error("Failed to fetch barcode!", error);
      }
    );
  }
  
  startMeasurement(): void {
    console.log("Starting measurement cycle...");

    this.http.post(`${this.BASE_URL}/reset_results`, {}).subscribe(
      (response: any) => {
          console.log("Backend results reset:", response);
          
          if (response?.result_counts && this.results.length === response.result_counts.length) {
              // Update values while retaining the original labels
              this.results.forEach((result, index) => {
                  result.value = response.result_counts[index];
              });
          }
      },
      (error) => {
          console.error("Failed to reset backend results:", error);
      }
  );


    const startProcess = (mode: string) => this.http.post(`${this.BASE_URL}/home_turntable_with_image`, {}).pipe(
      tap(() => console.log("Turntable homed successfully")),
      tap(() => { this.currentMeasurement++;}),
      switchMap(() => this.waitForTurntableDone()),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_center_circle`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_center_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_outer_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/update_results`, { mode: "full" })),
      tap((response: any) => this.updateResultsUI(response)),
      finalize(() => this.performMeasurementCycle())
    );

    if (!this.relayState) {
      this.toggleRelay();
      setTimeout(() => startProcess("full").subscribe(), 500);
    } else {
      startProcess("full").subscribe();
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
      tap(() => { this.currentMeasurement++;}),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_center_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_outer_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/update_results`, { mode: "slices" })),
      tap((response: any) => this.updateResultsUI(response)),
      finalize(() => {
        
        this.performMeasurementCycle();
      })
    ).subscribe();
  }
  

  waitForTurntableDone(): Observable<any> {
    return new Observable(observer => {
      const checkStatus = () => {
        this.http.get<{ connected: boolean; port?: string }>(`${this.BASE_URL}/status/serial/turntable`).subscribe(
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
  if (response?.result_counts) {
    if (!this.results || this.results.length !== response.result_counts.length) {
      // Initialize with default labels if results are empty or different in length
      this.results = response.result_counts.map((count: number, index: number) => ({
        label: `Result ${index + 1}`,
        value: count
      }));
    } else {
      // Update values but retain original labels
      this.results.forEach((result, index) => {
        result.value = response.result_counts[index];
      });
    }
    this.cdr.detectChanges();
  }
}

  // Tester Functions to analyse only parts of the images
  analyzeCenterCircle(): void {
    console.log("Analyzing Center Circle...");
    this.http.post(`${this.BASE_URL}/analyze_center_circle`, {}).pipe(
      tap(response => console.log("analyze_center_circle Response:", response)),  // Log response
      switchMap(() => {
        console.log("➡️ Calling update_results...");
        return this.http.post(`${this.BASE_URL}/update_results`, { mode: "center_circle" }, { headers: { 'Content-Type': 'application/json' } });
      }),
      tap((response: any) => {
        console.log("update_results Response:", response);
        this.updateResultsUI(response);
      })
    ).subscribe({
      error: (err) => console.error("Error in analyzeCenterCircle:", err)  // Log error if any
    });
  }

  analyzeInnerSlice(): void {
    console.log("Analyzing Center Slice...");
    this.http.post(`${this.BASE_URL}/analyze_center_slice`, {}).pipe(
      switchMap(() => this.http.post(`${this.BASE_URL}/update_results`, { mode: "center_slice" })),
      tap((response: any) => this.updateResultsUI(response))
    ).subscribe();
  }

  analyzeOuterSlice(): void {
    console.log("Analyzing Outer Slice...");
    this.http.post(`${this.BASE_URL}/analyze_outer_slice`, {}).pipe(
      switchMap(() => this.http.post(`${this.BASE_URL}/update_results`, { mode: "outer_slice" })),
      tap((response: any) => this.updateResultsUI(response))
    ).subscribe();
  }
}