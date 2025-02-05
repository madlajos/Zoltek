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
      console.log("Measurement cycle stopped.");
      // TODO: Stop measurement logic here
    }
  }

  analyzeImage(): void {
    this.http.post(`${this.BASE_URL}/analyze_image`, {}).subscribe(
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

    // Step 2: Call homing API and wait for it to return
    this.http.post(`${this.BASE_URL}/home_turntable_with_image`, {}).subscribe(
        (response: any) => {
            console.log("Turntable homed successfully:", response);

            // Step 3: Now capture an image and analyze it
            this.analyzeImage();
        },
        (error) => {
            console.error("Turntable homing failed!", error);
        }
    );
}

}
