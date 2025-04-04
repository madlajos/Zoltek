import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ViewChild, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { TurntableControlComponent } from '../turntable-control/turntable-control.component';
import { Observable, Subject, throwError } from 'rxjs';
import { catchError, switchMap, tap, takeUntil, finalize } from 'rxjs/operators';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { SharedService, MeasurementResult } from '../../shared.service';
import { MeasurementResultsPopupComponent } from '../../components/measurement-results-popup/measurement-results-popup.component';
import { SettingsUpdatesService } from '../../services/settings-updates.service';
import { BarcodeService } from '../../services/barcode.service';


@Component({
  standalone: true,
  selector: 'app-control-panel',
  templateUrl: './control-panel.component.html',
  styleUrls: ['./control-panel.component.css'],
  imports: [CommonModule, FormsModule, MatIconModule, TurntableControlComponent, MeasurementResultsPopupComponent]
})
export class ControlPanelComponent implements OnInit, OnDestroy {
  private readonly BASE_URL = 'http://localhost:5000/api';

  relayState: boolean = false;
  nozzleId: string = "";
  nozzleBarcode: string = "";
  operatorId: string = "";
  ng_limit: number = 0;

  isMainConnected: boolean = false;
  isSideConnected: boolean = false;

  measurementValidationTriggered: boolean = false;

  measurementActive: boolean = false;
  isResultsPopupVisible: boolean = false;

  currentMeasurement: number = 0;
  totalMeasurements: number = 18;
  turntablePosition: number | string = '?';

  private measurementStop$ = new Subject<void>();

  @ViewChild(TurntableControlComponent) turntableControl!: TurntableControlComponent;

  get progressPercentage(): number {
    return (this.currentMeasurement / this.totalMeasurements) * 100;
  }

  results: { label: string, value: number }[] = [
    { label: 'Eldugult', value: 0 },
    { label: 'Részleges', value: 0 },
    { label: 'Tiszta', value: 0 }
  ];

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
    private sharedService: SharedService,
    private settingsUpdatesService: SettingsUpdatesService,
    private barcodeService: BarcodeService
  ) { }

  ngOnInit(): void {
    this.barcodeService.barcode$.subscribe(newBarcode => {
      // If a measurement is active, ignore new barcodes.
      if (this.measurementActive) {
        return;
      }
      if (newBarcode) {
        console.log("New barcode from service:", newBarcode);
        this.nozzleBarcode = newBarcode;
        this.cdr.detectChanges();
      }
    });

    this.sharedService.cameraConnectionStatus$.subscribe(status => {
      this.isMainConnected = status.main;
      this.isSideConnected = status.side;
    });

    // Load initial size limits from backend.
    this.http.get<{ size_limits: { [key: string]: number } }>(`${this.BASE_URL}/get-other-settings?category=size_limits`)
      .subscribe({
        next: response => {
          if (response && response.size_limits) {
            // Access ng_limit with bracket notation.
            this.ng_limit = response.size_limits['ng_limit'];
            console.log("ng_limit loaded initially:", this.ng_limit);
          }
        },
        error: error => {
          console.error("Error loading settings:", error);
        }
      });

    // Subscribe to size limits updates via the shared service.
    this.settingsUpdatesService.sizeLimits$.subscribe(limits => {
      // Use bracket notation to access ng_limit.
      this.ng_limit = limits['ng_limit'];
      console.log("ng_limit updated via shared service:", this.ng_limit);
      this.cdr.detectChanges();
    });
  }

  ngOnDestroy(): void {
    this.measurementStop$.next();
    this.measurementStop$.complete();
  }

  ngAfterViewInit(): void {
    if (!this.turntableControl) {
      console.error("TurntableControlComponent is not available!");
    }
  }

  showResultsPopup(): void {
    this.isResultsPopupVisible = true;
  }

  get resultsValues(): number[] {
    return this.results.map(r => r.value);
  }

  canStartMeasurement(): boolean {
    if (!this.isMainConnected) {
      console.error("Cannot start measurement: Main camera is not connected.");
      return false;
    }
    if (!this.isSideConnected) {
      console.error("Cannot start measurement: Side camera is not connected.");
      return false;
    }
    if (!this.turntableControl) {
      console.error("Cannot start measurement: Turntable controller is not available.");
      return false;
    }
    // Check that either nozzleId or nozzleBarcode is provided.
    if (!this.nozzleId && !this.nozzleBarcode) {
      console.error("Cannot start measurement: Nozzle identifier is missing.");
      return false;
    }
    if (!this.operatorId) {
      console.error("Cannot start measurement: Operator ID is missing.");
      return false;
    }
    return true;
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
    if (!this.measurementActive) {
      if (!this.canStartMeasurement()) {
        //Check if conditions are met to start measurement
        this.measurementValidationTriggered = true;
        this.cdr.detectChanges();
        return;
      }
      // If validations pass, reset the flag.
      this.measurementValidationTriggered = false;
      this.measurementActive = true;
      this.sharedService.setMeasurementActive(true);
      console.log("Measurement cycle started.");
      this.startMeasurement();
    } else { // Stop measurement.
      this.measurementActive = false;
      this.sharedService.setMeasurementActive(false);
      console.log("Measurement cycle stopping...");
      this.stopMeasurement();
    }
  }

  stopMeasurement(): void {
    this.measurementActive = false;
    this.currentMeasurement = 0;
    
    // Reset results while keeping original labels.
    this.results = this.results.map(res => ({ ...res, value: 0 }));
    
    this.nozzleId = "";
    this.nozzleBarcode = "";
    this.barcodeService.clearBarcode();
    this.toggleRelay();
    
    console.log("Results cleared, progress bar reset, and barcode fields cleared.");
  
    // Emit a value to cancel the measurement chain.
    this.measurementStop$.next();
  
    this.http.post(`${this.BASE_URL}/reset_results`, {}).subscribe({
      next: (response: any) => {
        console.log("Backend results reset:", response);
        if (response?.result_counts && this.results.length === response.result_counts.length) {
          this.results.forEach((result, index) => {
            result.value = response.result_counts[index];
          });
        }
      },
      error: (error) => {
        console.error("Failed to reset backend results:", error);
      }
    });
  }

  
  startMeasurement(): void {
    console.log("Starting measurement cycle...");
  
    // Reset backend results first
    this.http.post(`${this.BASE_URL}/reset_results`, {}).subscribe(
      (response: any) => {
        console.log("Backend results reset:", response);
        if (response?.result_counts && this.results.length === response.result_counts.length) {
          this.results.forEach((result, index) => {
            result.value = response.result_counts[index];
          });
        }
      },
      (error) => {
        console.error("Failed to reset backend results:", error);
      }
    );
  
    const startProcess = (mode: string) =>
      this.http.post(`${this.BASE_URL}/home_turntable_with_image`, {}).pipe(
        tap(() => console.log("Turntable homed successfully")),
        tap(() => { this.currentMeasurement++; }),
        switchMap(() => this.waitForTurntableDone()),
        switchMap(() => this.http.post(`${this.BASE_URL}/analyze_center_circle`, {})),
        switchMap(() => this.http.post(`${this.BASE_URL}/analyze_center_slice`, {})),
        switchMap(() => this.http.post(`${this.BASE_URL}/analyze_outer_slice`, {})),
        switchMap(() => this.http.post(`${this.BASE_URL}/calculate-statistics?mode=full`, {})),
        switchMap(() => this.http.post(`${this.BASE_URL}/update_results`, { mode: "full" })),
        tap((response: any) => this.updateResultsUI(response)),
        // Cancel chain if measurement is stopped.
        takeUntil(this.measurementStop$),
        catchError((err) => {
          console.error("Measurement cycle error:", err);
          this.stopMeasurement(); // Abort cycle on error.
          return throwError(() => err);
        }),
        finalize(() => {
          if (this.measurementActive) {
            this.performMeasurementCycle();
          } else {
            console.log("Measurement cycle cancelled, not continuing further.");
          }
        })
      );
  
    if (!this.relayState) {
      this.toggleRelay();
      setTimeout(() => startProcess("full").subscribe(), 500);
    } else {
      startProcess("full").subscribe();
    }
  }

  performMeasurementCycle(): void {
    if (!this.measurementActive) {
      console.log("Measurement cycle cancelled.");
      return;
    }
    if (this.currentMeasurement >= this.totalMeasurements) {
      console.log("Measurement cycle completed.");

      if (true) {
        this.saveResultsToCsv();
      }

      this.showResultsPopup();
      return;
    }
  
    console.log(`Starting measurement ${this.currentMeasurement + 1} of ${this.totalMeasurements}...`);
  
    this.http.post(`${this.BASE_URL}/move_turntable_relative`, { degrees: 20 }).pipe(
      tap(() => console.log("Turntable rotated 20°")),
      switchMap(() => this.waitForTurntableDone()),
      tap(() => { this.currentMeasurement++; }),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_center_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/analyze_outer_slice`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/calculate-statistics?mode=slices`, {})),
      switchMap(() => this.http.post(`${this.BASE_URL}/update_results`, { mode: "slices" })),
      tap((response: any) => this.updateResultsUI(response)),
      takeUntil(this.measurementStop$), // Cancel chain if measurement stopped.
      catchError((err) => {
        console.error("Error during measurement cycle:", err);
        this.stopMeasurement();
        return throwError(() => err);
      }),
      finalize(() => {
        if (this.measurementActive) {
          this.performMeasurementCycle();
        } else {
          console.log("Measurement cycle cancelled in finalize.");
        }
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

  onPopupClosed(): void {
    // Reset the measurement cycle.
    this.stopMeasurement();
    // Hide the popup.
    this.isResultsPopupVisible = false;
  }

  saveResultsToCsv(): void {
    // Use the available spinneret id (from nozzleId or nozzleBarcode)
    const spinneretId = this.nozzleBarcode || this.nozzleId;
    if (!spinneretId) {
      console.error("Cannot save CSV: No spinneret ID provided.");
      return;
    }
    // Prepare the payload. The endpoint will use the current date on the server to name the CSV.
    const payload = {
      spinneret_id: spinneretId
      // You can add other parameters if needed.
    };
  
    this.http.post(`${this.BASE_URL}/save_results_to_csv`, payload).subscribe({
      next: (resp: any) => {
        console.log("CSV saved successfully:", resp);
        // Optionally update the UI with resp.filename, etc.
      },
      error: (err: any) => {
        console.error("CSV saving failed:", err);
      }
    });
  }

  // Tester Functions to analyse only parts of the images
  analyzeCenterCircle(): void {
    console.log("Analyzing Center Circle...");
    this.http.post(`${this.BASE_URL}/analyze_center_circle`, {}).pipe(
      tap(response => console.log("analyze_center_circle Response:", response)),
      switchMap(() => {
        console.log("➡️ Calling update_results...");
        return this.http.post(`${this.BASE_URL}/update_results`, { mode: "center_circle" }, { headers: { 'Content-Type': 'application/json' } });
      }),
      tap((response: any) => {
        console.log("update_results Response:", response);
        this.updateResultsUI(response);
      })
    ).subscribe({
      error: (err) => console.error("Error in analyzeCenterCircle:", err)
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
