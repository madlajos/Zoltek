import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
// other imports...

@Component({
  selector: 'app-control-panel',
  templateUrl: './control-panel.component.html',
  styleUrls: ['./control-panel.component.css']
})
export class ControlPanelComponent implements OnInit {
  private readonly BASE_URL = 'http://localhost:5000';
  
  relayState: boolean = false;
  nozzleId: string = "";
  
  // Measurement cycle properties (simulate 6/18 for now)
  currentMeasurement: number = 6;
  totalMeasurements: number = 18;

  // New property: measurement active state
  measurementActive: boolean = false;

  get progressPercentage(): number {
    return (this.currentMeasurement / this.totalMeasurements) * 100;
  }

  // Array for result blocks
  results: { label: string, value: number }[] = [
    { label: 'Result 1', value: 0 },
    { label: 'Result 2', value: 0 },
    { label: 'Result 3', value: 0 }
  ];

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    // Any initialization code if needed.
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

  // New measurement toggle function
  toggleMeasurement(): void {
    this.measurementActive = !this.measurementActive;
    if (this.measurementActive) {
      console.log("Measurement cycle started.");
      // Insert logic to start measurement cycle here.
    } else {
      console.log("Measurement cycle stopped.");
      // Insert logic to stop measurement cycle here.
    }
  }

  startMeasurement(): void {
    if (!this.measurementActive) {
      this.measurementActive = true;
      this.simulateProgress();
    }
  }

  simulateProgress(): void {
    let interval = setInterval(() => {
      if (this.currentMeasurement < this.totalMeasurements) {
        this.currentMeasurement++;
  
        // 🔥 Ensure Angular detects changes
        console.log(`Progress: ${this.currentMeasurement}/${this.totalMeasurements}`);
        
      } else {
        clearInterval(interval);
        this.measurementActive = false; // Stop when complete
      }
    }, 500); // Adjust speed if needed
  }
}
