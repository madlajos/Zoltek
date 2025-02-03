import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, of } from 'rxjs';
import { catchError, switchMap, tap } from 'rxjs/operators';

@Component({
  selector: 'app-control-panel',
  templateUrl: './control-panel.component.html',
  styleUrls: ['./control-panel.component.css']
})
export class ControlPanelComponent implements OnInit {
  private readonly BASE_URL = 'http://localhost:5000';
  relayState: boolean = false;  // false = OFF, true = ON
  nozzleId: string = "";        // This will hold the scanned barcode

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.initializeBarcodePolling();
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

  // Rotate functions (unchanged)
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

  // Poll the backend for barcode data every second.
  initializeBarcodePolling(): void {
    interval(1000).pipe(
      switchMap(() => 
        this.http.get<{ barcode: string }>(`${this.BASE_URL}/api/get-barcode`)
          .pipe(
            catchError(error => {
              console.error("Error polling barcode:", error);
              return of({ barcode: "" });
            })
          )
      ),
      tap(response => {
        if (response && response.barcode) {
          this.nozzleId = response.barcode;
          console.log("Barcode received:", response.barcode);
        }
      })
    ).subscribe();
  }
}
