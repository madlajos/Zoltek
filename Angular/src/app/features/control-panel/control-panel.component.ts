import { Component, OnInit, ViewChild } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { TurntableControlComponent } from '../turntable-control/turntable-control.component'; // Correct import
import { Observable } from 'rxjs';

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

  constructor(private http: HttpClient) {}

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
  rotateUp(): void {
    const payload = { degrees: 20 };
    this.http.post(`${this.BASE_URL}/move_turntable_relative`, payload).subscribe(
      (response: any) => {
        console.log("Turntable moved up 20 degrees", response);
      },
      (error) => {
        console.error("Error moving turntable up:", error);
      }
    );
  }

  rotateDown(): void {
    const payload = { degrees: -20 };
    this.http.post(`${this.BASE_URL}/move_turntable_relative`, payload).subscribe(
      (response: any) => {
        console.log("Turntable moved down 20 degrees", response);
      },
      (error) => {
        console.error("Error moving turntable down:", error);
      }
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

        // Stop any ongoing measurement cycle
        this.measurementActive = false;

        // Immediately reset progress and results
        this.currentMeasurement = 0;
        this.results = [
            { label: 'Result 1', value: 0 },
            { label: 'Result 2', value: 0 },
            { label: 'Result 3', value: 0 }
        ];

        console.log("Results cleared, progress bar set to 0.");

        // Turn off the relay
        if (this.relayState) {
            this.toggleRelay();
        }

        console.log("Relay turned off. Measurement cycle fully stopped.");
    }
}



  analyzeImage(): void {
    this.http.post(`${this.BASE_URL}/analyze_center_circle`, {}).subscribe(
      (response: any) => {
        console.log("Image analysis successful:", response);
        
        // Store results for UI update
        if (response.dot_contours) {
          this.results = response.dot_contours.map((dot: any) => ({
            label: `Dot ${dot.id}`,
            value: dot.area
          }));
        }
  
      },
      (error) => {
        console.error("Image analysis failed!", error);
      }
    );
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

    // Step 1: Ensure relay is ON
    if (!this.relayState) {
        this.toggleRelay();
    }
    console.log("Relay is ON. Proceeding to homing step...");

    // Step 2: Home the turntable
    this.http.post(`${this.BASE_URL}/home_turntable_with_image`, {}).subscribe(
        (homeResponse: any) => {
            console.log("Turntable homed successfully:", homeResponse);
            this.waitForTurntableDone(() => {
                console.log("First homing cycle confirmed DONE.");

                // Reset measurement count before the first analysis
                this.currentMeasurement = 0;

                // **First measurement includes all three analyses**
                this.http.post(`${this.BASE_URL}/analyze_center_circle`, {}).subscribe(
                    (circleResponse: any) => {
                        console.log("Center circle analysis completed:", circleResponse);
                        this.http.post(`${this.BASE_URL}/analyze_center_slice`, {}).subscribe(
                            (sliceResponse: any) => {
                                console.log("Center slice analysis completed:", sliceResponse);
                                this.http.post(`${this.BASE_URL}/analyze_outer_slice`, {}).subscribe(
                                    (outerResponse: any) => {
                                        console.log("Outer slice analysis completed:", outerResponse);
                                        this.http.post(`${this.BASE_URL}/update_results`, {}).subscribe(
                                            (sortResponse: any) => {
                                                console.log("Sorting (evaluation) complete:", sortResponse);
                                                this.results = sortResponse.result_counts.map((count: number, index: number) => ({
                                                    label: `Result ${index + 1}`,
                                                    value: count
                                                }));

                                                // After first image analysis, proceed with the measurement cycle
                                                this.currentMeasurement = 1;
                                                this.performMeasurementCycle();
                                            },
                                            (sortError) => {
                                                console.error("Sorting algorithm failed!", sortError);
                                            }
                                        );
                                    },
                                    (outerError) => {
                                        console.error("Outer slice analysis failed!", outerError);
                                    }
                                );
                            },
                            (sliceError) => {
                                console.error("Center slice analysis failed!", sliceError);
                            }
                        );
                    },
                    (circleError) => {
                        console.error("Center circle analysis failed!", circleError);
                    }
                );
            });
        },
        (homeError) => {
            console.error("Turntable homing failed!", homeError);
        }
    );
}

  

performMeasurementCycle(): void {
  if (!this.measurementActive) {
      console.log("Measurement cycle was stopped.");
      return;
  }

  if (this.currentMeasurement >= this.totalMeasurements) {
      console.log("Measurement cycle completed.");
      return;
  }

  console.log(`Starting measurement ${this.currentMeasurement + 1} of ${this.totalMeasurements}...`);

  // Rotate turntable before analyzing the next image
  this.http.post(`${this.BASE_URL}/move_turntable_relative`, { degrees: 20 }).subscribe(
      (rotationResponse: any) => {
          console.log("Turntable rotated 20° successfully:", rotationResponse);
          this.waitForTurntableDone(() => {
              if (!this.measurementActive) {
                  console.log("Measurement cycle was stopped after rotation.");
                  return;
              }

              console.log("Turntable movement confirmed. Proceeding with analysis...");

              // Analyze center slice and outer slice
              this.http.post(`${this.BASE_URL}/analyze_center_slice`, {}).subscribe(
                  (sliceResponse: any) => {
                      console.log(`Center slice analysis successful for measurement ${this.currentMeasurement + 1}:`, sliceResponse);
                      this.http.post(`${this.BASE_URL}/analyze_outer_slice`, {}).subscribe(
                          (outerResponse: any) => {
                              console.log(`Outer slice analysis successful for measurement ${this.currentMeasurement + 1}:`, outerResponse);
                              this.http.post(`${this.BASE_URL}/update_results`, {}).subscribe(
                                  (sortResponse: any) => {
                                      console.log(`Sorting complete for measurement ${this.currentMeasurement + 1}:`, sortResponse);
                                      this.results = sortResponse.result_counts.map((count: number, index: number) => ({
                                          label: `Result ${index + 1}`,
                                          value: count
                                      }));

                                      // Only increment after successful processing
                                      this.currentMeasurement++;

                                      if (!this.measurementActive) {
                                          console.log("Measurement cycle was stopped before next rotation.");
                                          return;
                                      }

                                      // Continue measurement cycle until complete
                                      this.performMeasurementCycle();
                                  },
                                  (sortError) => {
                                      console.error("Sorting algorithm failed!", sortError);
                                  }
                              );
                          },
                          (outerError) => {
                              console.error("Outer slice analysis failed!", outerError);
                          }
                      );
                  },
                  (sliceError) => {
                      console.error("Center slice analysis failed!", sliceError);
                  }
              );
          });
      },
      (rotationError) => {
          console.error("Failed to move turntable!", rotationError);
      }
  );
}

  

waitForTurntableDone(callback: () => void): void {
    console.log("Waiting for turntable movement to complete...");

    const checkStatus = () => {
        this.http.get<{ connected: boolean; port?: string }>(`${this.BASE_URL}/api/status/serial/turntable`).subscribe(
            (statusResponse) => {
                if (statusResponse.connected) {
                    console.log("Turntable movement completed.");
                    callback(); // Proceed to next measurement
                } else {
                    setTimeout(checkStatus, 500); // Retry in 500ms
                }
            },
            (statusError) => {
                console.error("Error checking turntable status!", statusError);
                setTimeout(checkStatus, 500); // Retry on failure
            }
        );
    };

    checkStatus();
}


}
